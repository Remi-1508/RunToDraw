"""Recherche du meilleur itinéraire pour une forme ou un texte donné.

Le principe est le même pour une forme et pour une lettre : on génère un
ensemble de candidats (position, taille, angle), on projette chacun sur le
graphe routier (`route_from_target`), on le note (`scoring.score_solution`),
et on garde le meilleur.

Deux résultats sont conservés par recherche :
- `closest_to_distance` : le candidat le plus proche de la distance demandée,
- `best_compromise` : le meilleur compromis forme/distance/fluidité.
"""

import math
from concurrent.futures import as_completed

import numpy as np

from . import geometry as geo
from .scoring import score_solution
from .shapes import GLYPHS, single_letter_polyline

_TEXT_CANDIDATE_SAMPLES = 60
_SHAPE_CANDIDATE_SAMPLES = 72
_LETTER_CANDIDATE_SAMPLES = 64

# Nombre fixe de candidats testés par lettre en mode "lettres indépendantes"
# (7 centres locaux x 5 angles x 5 tailles) : utile pour annoncer un total de
# candidats à l'avance, avant de lancer la recherche (voir planner.py).
_LETTER_CANDIDATES_PER_LETTER = 7 * 5 * 5


# ---------------------------------------------------------------------------
# Aide au routage : projeter une forme cible sur le graphe et reconstruire
# un trajet réel à partir des nœuds accrochés.
# ---------------------------------------------------------------------------

def _simplify_consecutive_duplicates(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


def route_from_target(graph, target_points, sample_count=60):
    """Accroche la forme cible au graphe et relie les nœuds par plus courts chemins."""
    target_rs = geo.resample_polyline(target_points, n_samples=sample_count)

    snapped = []
    snap_dists = []
    for p in target_rs:
        nid, d = graph.nearest_node(p)
        snapped.append(nid)
        snap_dists.append(d)

    snapped = _simplify_consecutive_duplicates(snapped)

    full_path = []
    total_cost = 0.0
    unreachable = 0

    for a, b in zip(snapped[:-1], snapped[1:]):
        sp, cost = graph.shortest_path(a, b)
        if sp is None:
            unreachable += 1
            continue
        if not full_path:
            full_path.extend(sp)
        else:
            full_path.extend(sp[1:])
        total_cost += cost

    if full_path:
        route_points = graph.path_to_points(full_path)
        route_points = geo.simplify_path_points(route_points, angle_tol_deg=6.0)
    else:
        route_points = np.empty((0, 2), dtype=float)

    extra = {
        "snap_mean": float(np.mean(snap_dists)) if snap_dists else float("inf"),
        "shortest_path_cost": total_cost,
        "unreachable_segments": unreachable,
        "n_route_nodes": len(full_path),
    }
    return full_path, route_points, extra


# ---------------------------------------------------------------------------
# Génération des candidats : centres, tailles, angles.
# ---------------------------------------------------------------------------

def graph_center(graph):
    return np.array([
        0.5 * (graph.bounds["xmin"] + graph.bounds["xmax"]),
        0.5 * (graph.bounds["ymin"] + graph.bounds["ymax"]),
    ], dtype=float)


def dominant_graph_angle(graph, max_edges=2000):
    """Estime l'orientation dominante des rues, pour aligner les formes dessus."""
    angles = []
    count = 0

    for u, lst in graph.adj.items():
        pu = graph.node_xy.get(u)
        if pu is None:
            continue
        for e in lst:
            pv = graph.node_xy.get(e.to)
            if pv is None:
                continue
            v = pv - pu
            n = np.linalg.norm(v)
            if n < 5.0:
                continue
            ang = math.degrees(math.atan2(v[1], v[0]))
            while ang < -90:
                ang += 180
            while ang > 90:
                ang -= 180
            angles.append(ang)
            count += 1
            if count >= max_edges:
                break
        if count >= max_edges:
            break

    if not angles:
        return 0.0

    bins = np.arange(-90, 91, 10)
    hist, edges = np.histogram(angles, bins=bins)
    idx = int(np.argmax(hist))
    return float(0.5 * (edges[idx] + edges[idx + 1]))


def estimate_size_candidates(base_points, desired_distance_m, shape_name):
    """Construit plusieurs tailles candidates autour de la taille nominale demandée."""
    base_len = max(geo.polyline_length(base_points), 1e-9)
    base_size = desired_distance_m / max(base_len, 1e-9)

    if shape_name == "text":
        factors = [0.45, 0.60, 0.75, 0.90, 1.05]
    elif shape_name in {"heart", "star", "infinity", "circle", "square"}:
        factors = [0.65, 0.80, 0.95, 1.10]
    else:
        factors = [0.75, 0.90, 1.00, 1.10]

    return [max(80.0, base_size * f) for f in factors]


def make_candidate_points(base_points, center, size_m, angle_deg):
    """Construit un candidat transformé à partir d'une forme de base : taille + rotation + translation."""
    pts = geo.fit_points(base_points, np.array([0.0, 0.0], dtype=float), size_m)
    pts = geo.rotate_points(pts, angle_deg)
    pts[:, 0] += center[0]
    pts[:, 1] += center[1]
    return pts


def global_search_candidates(graph, base_points, desired_distance_m, shape_name, use_translation):
    """Génère tous les candidats (centre, taille, angle) pour une forme.

    Le mode translation explore quelques centres décalés autour du centre du
    graphe ; le mode projection n'utilise que le centre du graphe lui-même.
    """
    center = graph_center(graph)
    width = graph.bounds["xmax"] - graph.bounds["xmin"]
    height = graph.bounds["ymax"] - graph.bounds["ymin"]
    step = 0.12 * min(width, height)

    if shape_name == "text":
        step *= 0.95

    if use_translation:
        centers = [
            center,
            center + np.array([step, 0.0]),
            center + np.array([-step, 0.0]),
            center + np.array([0.0, step]),
            center + np.array([0.0, -step]),
        ]
    else:
        centers = [center]

    base_angle = dominant_graph_angle(graph)

    if shape_name == "text":
        angles = [base_angle - 25, base_angle - 12, base_angle, base_angle + 12, base_angle + 25]
    else:
        angles = [base_angle + a for a in (-60, -45, -30, -15, 0, 15, 30, 45, 60)]

    sizes = estimate_size_candidates(base_points, desired_distance_m, shape_name)

    candidates = []
    for c in centers:
        for a in angles:
            for s in sizes:
                candidates.append((c.copy(), float(s), float(a)))
    return candidates


# ---------------------------------------------------------------------------
# Évaluation : essaie tous les candidats et garde les meilleurs.
#
# Chaque candidat est indépendant des autres (position/taille/angle -> accroche
# au graphe -> Dijkstra -> note). Le paramètre `executor` optionnel (voir
# `parallel.py`) répartit ce travail sur quelques threads ; à None, tout
# reste séquentiel. Un vrai pool de PROCESSUS a été essayé en premier mais
# mesuré plus lent que le séquentiel une fois le KD-tree en place : le coût
# de sérialisation entre processus dépasse le travail (quelques ms) par
# candidat. Les threads partagent la mémoire du graphe (pas de pickling) et
# une bonne partie du travail (KD-tree scipy, numpy) relâche le GIL.
# ---------------------------------------------------------------------------

def evaluate_candidate(graph, base_points, center, size_m, angle_deg, desired_distance_m, max_allowed_m,
                        sample_count, extra_metrics=None):
    """Construit, route et note un unique candidat (position, taille, angle)."""
    target = make_candidate_points(base_points, center, size_m, angle_deg)
    node_path, route_points, extra = route_from_target(graph, target, sample_count=sample_count)

    metrics = score_solution(route_points, target, desired_distance_m, max_allowed_m)
    metrics.update(extra)
    metrics["angle_deg"] = angle_deg
    metrics["size_m"] = size_m
    if extra_metrics:
        metrics.update(extra_metrics)

    return {
        "target": target,
        "node_path": node_path,
        "route_points": route_points,
        "metrics": metrics,
    }


def _evaluate_all(graph, jobs, executor, on_progress=None):
    """Évalue une liste de jobs (arguments positionnels de evaluate_candidate).

    Threads partageant le même graphe en mémoire : pas de reconstruction ni
    de sérialisation nécessaires, juste une répartition du travail.
    `on_progress()`, si fourni, est appelé une fois par candidat terminé —
    c'est ce qui alimente la progression réelle d'une génération (voir
    `jobs.py`), plutôt qu'une barre de chargement simulée.
    """
    if executor is None:
        results = []
        for job in jobs:
            results.append(evaluate_candidate(graph, *job))
            if on_progress:
                on_progress()
        return results

    futures = [executor.submit(evaluate_candidate, graph, *job) for job in jobs]
    results = []
    for future in as_completed(futures):
        results.append(future.result())
        if on_progress:
            on_progress()
    return results


def count_variant_candidates(graph, base_points, desired_distance_m, shape_name):
    """Nombre total de candidats qu'évaluerait evaluate_method pour les deux méthodes.

    Permet de connaître à l'avance le total de travail d'une recherche de
    forme, avant de la lancer (pour annoncer une progression réelle).
    """
    return sum(
        len(global_search_candidates(graph, base_points, desired_distance_m, shape_name, use_translation))
        for use_translation in (False, True)
    )


def count_split_text_candidates(text):
    """Nombre total de candidats qu'évaluerait split_text_itineraries_full_distance."""
    letters = [ch for ch in (text or "").upper() if ch != " " and ch in GLYPHS]
    n_letters = max(len(letters), 1)
    return n_letters * _LETTER_CANDIDATES_PER_LETTER


def evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, method_name, executor=None,
                     on_progress=None):
    """Évalue tous les candidats d'une méthode (projection ou translation).

    Garde le candidat le plus proche de la distance demandée, et le meilleur
    compromis global entre forme, distance et fluidité.
    """
    max_allowed_m = desired_distance_m * (1.0 + tolerance_ratio)
    use_translation = (method_name == "translation")
    candidates = global_search_candidates(graph, base_points, desired_distance_m, shape_name, use_translation)
    sample_count = _TEXT_CANDIDATE_SAMPLES if shape_name == "text" else _SHAPE_CANDIDATE_SAMPLES

    jobs = [
        (base_points, center, size_m, angle_deg, desired_distance_m, max_allowed_m, sample_count,
         {"center_x": float(center[0]), "center_y": float(center[1])})
        for center, size_m, angle_deg in candidates
    ]
    evaluated = _evaluate_all(graph, jobs, executor, on_progress=on_progress)

    feasible = [e for e in evaluated if e["metrics"]["over_max"] <= 1e-6]

    if feasible:
        best_close = min(
            feasible,
            key=lambda e: (
                e["metrics"]["length_gap"],
                e["metrics"]["shape_error"],
                e["metrics"]["turn_penalty"],
            ),
        )
        best_comp = min(
            feasible,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["length_gap"],
            ),
        )
    else:
        best_close = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["over_max"],
                e["metrics"]["length_gap"],
                e["metrics"]["shape_error"],
            ),
        )
        best_comp = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["over_max"],
            ),
        )

    return {
        "closest_to_distance": best_close,
        "best_compromise": best_comp,
        "all_candidates_count": len(evaluated),
    }


# ---------------------------------------------------------------------------
# Mode texte "lettres indépendantes" : chaque lettre est cherchée à part et
# reçoit la distance complète demandée par l'utilisateur. C'est un choix
# volontaire, pas un raccourci : sur une même zone, une lettre seule peut
# souvent suivre la forme bien plus fidèlement que le mot entier compressé
# dans la même distance. Ce mode donne donc à l'utilisateur un second choix
# à comparer au mot complet (search.evaluate_method avec shape_name="text").
# ---------------------------------------------------------------------------

def split_text_itineraries_full_distance(graph, text, per_letter_distance_m, tolerance_ratio, executor=None,
                                          on_progress=None):
    letters = [ch for ch in (text or "").upper() if ch != " " and ch in GLYPHS]
    if not letters:
        letters = ["P"]

    n = len(letters)
    center = graph_center(graph)
    dom_angle = dominant_graph_angle(graph)

    a = math.radians(dom_angle)
    direction = np.array([math.cos(a), math.sin(a)], dtype=float)
    normal = np.array([-direction[1], direction[0]], dtype=float)

    width = graph.bounds["xmax"] - graph.bounds["xmin"]
    height = graph.bounds["ymax"] - graph.bounds["ymin"]
    span = min(width, height)

    spacing = 0.18 * span
    if n > 1:
        spacing = min(spacing, 0.75 * span / (n - 1))

    offsets = [((i - 0.5 * (n - 1)) * spacing) for i in range(n)]

    results = []
    for i, ch in enumerate(letters):
        base = single_letter_polyline(ch)
        anchor = center + direction * offsets[i]

        local_centers = [
            anchor,
            anchor + 0.18 * spacing * normal,
            anchor - 0.18 * spacing * normal,
            anchor + 0.10 * spacing * direction,
            anchor - 0.10 * spacing * direction,
            anchor + 0.12 * spacing * (direction + normal),
            anchor + 0.12 * spacing * (direction - normal),
        ]

        angles = [dom_angle - 25, dom_angle - 12, dom_angle, dom_angle + 12, dom_angle + 25]

        base_len = max(geo.polyline_length(base), 1e-9)
        nominal_size = per_letter_distance_m / base_len

        # "I" et "1" sont visuellement très étroites : elles ont besoin de
        # tailles plus grandes pour rester repérables une fois routées.
        if ch in {"I", "1"}:
            size_factors = [0.70, 0.85, 1.00, 1.15, 1.30]
        else:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]

        sizes = [max(120.0, nominal_size * f) for f in size_factors]
        max_allowed_m = per_letter_distance_m * (1.0 + tolerance_ratio)

        jobs = [
            (base, c, size, ang, per_letter_distance_m, max_allowed_m, _LETTER_CANDIDATE_SAMPLES, None)
            for c in local_centers
            for ang in angles
            for size in sizes
        ]
        evaluated = [dict(item, letter=ch) for item in _evaluate_all(graph, jobs, executor, on_progress=on_progress)]

        feasible = [e for e in evaluated if e["metrics"]["over_max"] <= 1e-6]

        if feasible:
            best = min(
                feasible,
                key=lambda e: (
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )
        else:
            best = min(
                evaluated,
                key=lambda e: (
                    e["metrics"]["over_max"],
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )

        best["target_distance"] = per_letter_distance_m
        results.append(best)

    return results
