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


# Mise en page de chaque lettre en mode séparé : polyligne de base, centres et tailles testés.
# `direction` est le sens de lecture (vecteur unitaire), `normal` lui est perpendiculaire.
def split_letter_layout(letters, per_letter_distance_m, direction, normal):
    n = len(letters)
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
        nominal_size = per_letter_distance_m / base_len

        if ch in {"I", "1"}:
            size_factors = [0.70, 0.85, 1.00, 1.15, 1.30]
        else:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]

        sizes = [max(120.0, nominal_size * f) for f in size_factors]
        layout.append((ch, base, local_centers, sizes))
    return layout


def split_text_itineraries_full_distance(graph, text, per_letter_distance_m, tolerance_ratio):
    letters = split_letters(text)
    # Lettres droites, lues de gauche à droite (voir ORIENTATION_RULES).
    angles = search_angles(graph, "text")
    direction = np.array([1.0, 0.0], dtype=float)
    normal = np.array([0.0, 1.0], dtype=float)

    # 1) Chaque lettre est évaluée pour tous les angles.
    per_letter = []
    for ch, base, local_centers, sizes in split_letter_layout(letters, per_letter_distance_m, direction, normal):
        evaluated = calibrated_search(
            graph, base, local_centers, angles,
            per_letter_distance_m, per_letter_distance_m * (1.0 + tolerance_ratio),
            sample_count=64, min_size=min(sizes), max_size=max(sizes),
        )
        per_letter.append((ch, evaluated))

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
    for ch, evaluated in per_letter:
        best = best_at(evaluated, best_angle) if best_angle is not None else pick_best(evaluated)[0]
        best["letter"] = ch
        best["target_distance"] = per_letter_distance_m
        results.append(best)

    return results


# « Lettres reliées » : un seul parcours qui dessine les lettres l'une après l'autre.
# Les lettres calculées par split_text_itineraries_full_distance sont gardées telles quelles ; deux
# lettres consécutives sont reliées par le plus court chemin sur le réseau. Chaque lettre peut être
# parcourue dans un sens ou dans l'autre : le sens de chaque lettre est choisi pour minimiser la
# longueur totale des liaisons (programmation dynamique à 2 états par lettre : 4 plus courts chemins
# par paire de lettres, coût linéaire en nombre de lettres).

def link_letter_routes(graph, letter_results):
    """Renvoie (morceaux, longueur totale) ; morceaux = liste de dicts
    {"kind": "letter" | "link", "letter": str | None, "node_path": [indices de nœuds]}."""
    paths = [[graph._idx_of[n] for n in r["node_path"]] for r in letter_results]
    paths = [p for p in paths if p]
    letters = [r["letter"] for r in letter_results if r["node_path"]]
    if not paths:
        return [], 0.0

    def oriented(i, reverse):
        return paths[i][::-1] if reverse else paths[i]

    # coût[i][r] = longueur minimale des liaisons jusqu'à la lettre i parcourue dans le sens r
    cost = [[0.0, 0.0]]
    back = [[None, None]]
    links = [{}]
    for i in range(1, len(paths)):
        cost.append([math.inf, math.inf]); back.append([None, None]); links.append({})
        for r in (0, 1):
            start = oriented(i, r)[0]
            for pr in (0, 1):
                end = oriented(i - 1, pr)[-1]
                link, c = graph.shortest_path_idx(end, start)
                if link is None:
                    continue
                total = cost[i - 1][pr] + c
                if total < cost[i][r]:
                    cost[i][r], back[i][r] = total, pr
                    links[i][r] = link

    r = 0 if cost[-1][0] <= cost[-1][1] else 1
    if math.isinf(cost[-1][r]):
        return [], 0.0
    choice = [0] * len(paths)
    for i in range(len(paths) - 1, -1, -1):
        choice[i] = r
        if i > 0:
            r = back[i][r]

    pieces = []
    for i in range(len(paths)):
        if i > 0:
            link = links[i][choice[i]]
            if len(link) > 1:
                pieces.append({"kind": "link", "letter": None, "node_path": link})
        pieces.append({"kind": "letter", "letter": letters[i], "node_path": oriented(i, choice[i])})

    full = []
    for piece in pieces:
        full.extend(piece["node_path"] if not full else piece["node_path"][1:])
    return pieces, polyline_length(graph.node_array[full])
