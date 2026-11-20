"""Mode texte : chaque lettre est cherchée indépendamment (avec la distance complète demandée),
puis les lettres peuvent être reliées en un seul parcours."""
import math

import numpy as np

from runtodraw.geometry import polyline_length
from runtodraw.glyphs import GLYPHS, single_letter_polyline
from runtodraw.search import calibrated_search, pick_best, search_angles, search_frame


# Lettres à dessiner en mode séparé (caractères inconnus ignorés, "P" s'il ne reste rien).
def split_letters(text):
    letters = [ch for ch in (text or "").upper() if ch != " " and ch in GLYPHS]
    return letters or ["P"]


# Distance visée pour chaque lettre. Toutes les lettres ne demandent pas le même effort pour la même
# hauteur : un F (trait vertical, deux barres) est plus long à tracer qu'un C. Si chaque lettre visait
# exactement la même distance, un C serait dessiné beaucoup plus grand qu'un F. On vise donc une distance
# proportionnelle à la longueur du tracé de la lettre, ce qui donne des lettres de même hauteur.
# La moyenne reste la distance demandée (la distance totale du mot ne change pas) ; le rapport est borné
# pour qu'une lettre très courte ou très longue ne s'éloigne pas trop de la distance demandée.
LETTER_DISTANCE_RATIO_RANGE = (0.7, 1.4)


def letter_target_distances(letters, per_letter_distance_m):
    lengths = [max(polyline_length(single_letter_polyline(ch)), 1e-9) for ch in letters]
    mean_length = sum(lengths) / len(lengths)
    low, high = LETTER_DISTANCE_RATIO_RANGE
    return [per_letter_distance_m * min(max(length / mean_length, low), high) for length in lengths]


# Mise en page de chaque lettre en mode séparé : polyligne de base, centres, tailles testés
# et distance visée. `direction` est le sens de lecture (vecteur unitaire), `normal` lui est perpendiculaire.
def split_letter_layout(letters, per_letter_distance_m, direction, normal):
    n = len(letters)
    targets = letter_target_distances(letters, per_letter_distance_m)
    center, span = search_frame(per_letter_distance_m)

    spacing = 0.18 * span
    if n > 1:
        spacing = min(spacing, 0.75 * span / (n - 1))

    offsets = [((i - 0.5 * (n - 1)) * spacing) for i in range(n)]

    layout = []
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

        base_len = max(polyline_length(base), 1e-9)
        nominal_size = targets[i] / base_len

        if ch in {"I", "1"}:
            size_factors = [0.70, 0.85, 1.00, 1.15, 1.30]
        else:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]

        sizes = [max(120.0, nominal_size * f) for f in size_factors]
        layout.append((ch, base, local_centers, sizes, targets[i]))
    return layout


def split_text_itineraries_full_distance(graph, text, per_letter_distance_m, tolerance_ratio):
    letters = split_letters(text)
    # Lettres droites, lues de gauche à droite (voir ORIENTATION_RULES).
    angles = search_angles(graph, "text")
    direction = np.array([1.0, 0.0], dtype=float)
    normal = np.array([0.0, 1.0], dtype=float)

    # 1) Chaque lettre est évaluée pour tous les angles.
    per_letter = []
    targets = {}
    for i, (ch, base, local_centers, sizes, target_m) in enumerate(
        split_letter_layout(letters, per_letter_distance_m, direction, normal)
    ):
        evaluated = calibrated_search(
            graph, base, local_centers, angles,
            target_m, target_m * (1.0 + tolerance_ratio),
            sample_count=64, min_size=min(sizes), max_size=max(sizes),
        )
        per_letter.append((ch, evaluated))
        targets[i] = target_m

    # 2) Une seule orientation pour tout le mot : des lettres inclinées différemment sont illisibles.
    # Pour chaque angle, on prend le meilleur candidat de chaque lettre à cet angle et on additionne
    # leurs scores ; l'angle au total le plus bas l'emporte.
    def best_at(evaluated, angle):
        same_angle = [e for e in evaluated if abs(e["metrics"]["angle_deg"] - angle) < 1e-9]
        return pick_best(same_angle)[0] if same_angle else None

    best_angle, best_total = None, float("inf")
    for angle in angles:
        picks = [best_at(evaluated, angle) for _, evaluated in per_letter]
        if any(p is None for p in picks):
            continue
        total = sum(
            p["metrics"]["combined"] + 0.12 * p["metrics"]["over_max"] + 0.12 * p["metrics"].get("under_min", 0.0)
            for p in picks
        )
        if total < best_total:
            best_angle, best_total = angle, total

    results = []
    for i, (ch, evaluated) in enumerate(per_letter):
        best = best_at(evaluated, best_angle) if best_angle is not None else pick_best(evaluated)[0]
        best["letter"] = ch
        best["target_distance"] = targets[i]
        results.append(best)

    return results


# « Lettres reliées » : un seul parcours qui dessine les lettres l'une après l'autre.
# Les lettres calculées par split_text_itineraries_full_distance sont gardées telles quelles ; deux
# lettres consécutives sont reliées par le plus court chemin sur le réseau. Chaque lettre peut être
# parcourue dans un sens ou dans l'autre : le sens de chaque lettre est choisi pour minimiser la
# longueur totale des liaisons (programmation dynamique à 2 états par lettre : 4 plus courts chemins
# par paire de lettres, coût linéaire en nombre de lettres).

def _corner_index(graph, path, right):
    """Indice (dans `path`) du nœud le plus proche du coin bas-droit (ou bas-gauche) de la lettre."""
    xy = graph.node_array[path]
    corner = np.array([xy[:, 0].max() if right else xy[:, 0].min(), xy[:, 1].min()])
    return int(np.argmin(np.hypot(*(xy - corner).T)))


def _underline_walk(graph, path, anchors, left_idx, right_idx):
    """Parcours d'une lettre qui commence à son coin bas-gauche et finit à son coin bas-droit.

    Le tracé de la lettre est continu mais commence et finit n'importe où ; pour relier deux lettres par
    leur bas (comme un soulignement), on revient en arrière sur le tracé déjà dessiné :
    coin bas-gauche -> début, tout le tracé, fin -> coin bas-droit. Les deux sens de parcours sont essayés
    et on garde celui qui demande le moins de retours en arrière. Renvoie (nœuds, positions des ancrages).
    """
    best = None
    n = len(path)
    for reverse in (False, True):
        p = path[::-1] if reverse else path
        a = [n - 1 - x for x in reversed(anchors)] if reverse else list(anchors)
        left = n - 1 - left_idx if reverse else left_idx
        right = n - 1 - right_idx if reverse else right_idx
        pre = p[left:0:-1]  # du coin bas-gauche jusqu'au 2e nœud (le 1er ouvre le tracé principal)
        post = [p[j] for j in range(n - 2, right - 1, -1)]  # de l'avant-dernier nœud au coin bas-droit (vide si c'est la fin)
        extra = polyline_length(graph.node_array[pre + p[:1]]) if pre else 0.0
        extra += polyline_length(graph.node_array[p[-1:] + post]) if post else 0.0
        if best is None or extra < best[0]:
            best = (extra, pre + p + post, [len(pre) + x for x in a])
    return best[1], best[2]


def link_letter_routes(graph, letter_results):
    """Renvoie (morceaux, longueur totale) ; morceaux = liste de dicts
    {"kind": "letter" | "link", "letter": str | None, "node_path": [indices de nœuds], "anchors": [positions]}.

    Les lettres sont reliées comme un soulignement : chaque lettre est parcourue du coin bas-gauche au coin
    bas-droit, et la liaison va du bas-droit d'une lettre au bas-gauche de la suivante (au lieu de diagonales
    entre un début et une fin de tracé quelconques). Les liaisons sont toujours présentes (même vides,
    d'un seul nœud) : ainsi, déplacer le bord d'une lettre à la main peut les rallonger."""
    paths = [[graph._idx_of[n] for n in r["node_path"]] for r in letter_results]
    anchor_lists = [list(r.get("anchor_idx", [])) for r in letter_results]
    keep = [i for i, p in enumerate(paths) if p]
    paths = [paths[i] for i in keep]
    anchor_lists = [anchor_lists[i] for i in keep]
    letters = [r["letter"] for r in letter_results if r["node_path"]]
    if not paths:
        return [], 0.0

    walks = []
    for path, anchors in zip(paths, anchor_lists):
        left = _corner_index(graph, path, right=False)
        right = _corner_index(graph, path, right=True)
        walks.append(_underline_walk(graph, path, anchors, left, right))

    pieces = []
    for i, (walk, anchors) in enumerate(walks):
        if i > 0:
            link, _ = graph.shortest_path_idx(walks[i - 1][0][-1], walk[0])
            if link is None:
                return [], 0.0
            pieces.append({"kind": "link", "letter": None, "node_path": link, "anchors": []})
        pieces.append({"kind": "letter", "letter": letters[i], "node_path": walk, "anchors": anchors})

    full = []
    for piece in pieces:
        full.extend(piece["node_path"] if not full else piece["node_path"][1:])
    return pieces, polyline_length(graph.node_array[full])
