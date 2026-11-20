"""Planificateur : transforme les résultats du moteur en propositions d'itinéraires (lat/lon) pour l'API."""
import logging
import math
import time
from contextlib import contextmanager
from typing import Any, Dict, List

from runtodraw.geometry import xy_array_to_latlon
from runtodraw.search import evaluate_method, evaluate_start_method
from runtodraw.shapes import get_base_shape
from runtodraw.text_routes import link_letter_routes, split_text_itineraries_full_distance

logger = logging.getLogger(__name__)


# Chronomètre une phase du calcul et l'écrit dans les logs (visibles sur Render) : sert à repérer ce qui prend
# du temps avant d'optimiser. Le coût de la mesure est négligeable.
@contextmanager
def timed(phase):
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info("Phase « %s » : %.1f s", phase, time.perf_counter() - start)


# Un trajet candidat est d’abord calculé en coordonnées locales.
# Cette fonction reconvertit toute la polyligne en points GPS.
def route_points_xy_to_latlon(graph, route_points):
    return xy_array_to_latlon(route_points, graph.center_lat, graph.center_lon)


# Cette fonction met en forme un segment d’itinéraire dans la structure attendue
# par le frontend. On garde un label, les points GPS et la distance mesurée, ainsi que les identifiants
# des nœuds du chemin et la position des points d'ancrage (sommets modifiables sur la carte).
def build_segment_from_candidate(graph, candidate, label):
    metrics = candidate.get("metrics", {})

    # On envoie le chemin complet, nœud par nœud, pour que le tracé affiché et l'export GPX
    # suivent exactement les rues. (La polyligne simplifiée ne sert qu'en interne, pour l'évaluation.)
    node_path = candidate.get("node_path")
    if node_path:
        route_points = graph.path_to_points(node_path)
    else:
        route_points = candidate.get("route_points")

    latlon_points = route_points_xy_to_latlon(graph, route_points) if route_points is not None else []

    return {
        "label": label,
        "points": latlon_points,
        "distance_m": float(metrics.get("length_route", 0.0)),
        "node_path": list(node_path) if node_path else [],
        "anchors": list(candidate.get("anchor_idx", [])),
    }


SHAPE_LABELS = {
    "heart": "Cœur",
    "square": "Carré",
    "circle": "Rond",
    "star": "Étoile",
    "infinity": "Infini",
    "triangle": "Triangle",
    "diamond": "Losange",
    "lightning": "Éclair",
    "custom": "Mon dessin",
}

METHODS = [
    ("projection", "Projection"),
    ("translation", "Translation"),
    ("start", "Départ inclus"),
]

VARIANTS = [
    ("closest_to_distance", "distance la plus proche"),
    ("best_compromise", "meilleur compromis"),
]


def route_metrics(metrics):
    return {
        "total_distance_m": float(metrics.get("length_route", 0.0)),
        "length_gap_m": float(metrics.get("length_gap", 0.0)),
        "shape_error": float(metrics.get("shape_error", 0.0)),
        "turn_penalty": float(metrics.get("turn_penalty", 0.0)),
        "over_max_m": float(metrics.get("over_max", 0.0)),
    }


# Lance les trois méthodes de recherche sur un dessin (forme ou mot entier) et met en forme
# chaque résultat (méthode, variante) comme une proposition d'itinéraire.
def method_routes(graph, base_points, distance_m, tolerance_ratio, shape_name, label, kind):
    results = {}
    with timed(f"{label} : projection"):
        results["projection"] = evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, "projection")
    with timed(f"{label} : translation"):
        results["translation"] = evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, "translation",
                                                 angle_hint=results["projection"]["ranked_angles"])
    with timed(f"{label} : départ inclus"):
        results["start"] = evaluate_start_method(graph, base_points, distance_m, tolerance_ratio, shape_name,
                                                 angle_hint=results["projection"]["ranked_angles"])
    routes = []
    for method_name, method_label in METHODS:
        for variant_name, variant_label in VARIANTS:
            candidate = results[method_name][variant_name]
            routes.append({
                "label": label,
                "kind": kind,
                "variant": f"{method_label} – {variant_label}",
                "_tags": [(method_label, variant_label)],
                "includes_start": method_name == "start",
                **route_metrics(candidate["metrics"]),
                "segments": [build_segment_from_candidate(graph, candidate, label)],
                "_key": tuple(candidate.get("node_path") or ()),
            })
    return routes


# Supprime les propositions en double. Le même trajet est souvent trouvé par plusieurs méthodes ou
# variantes (ex. la meilleure translation est la position centrée : elle égale la projection). Les trajets
# identiques (mêmes nœuds, dans le même ordre) sont fusionnés et leurs libellés regroupés.
def merged_variant_label(tags):
    """[(méthode, variante), ...] -> « Projection – distance la plus proche et meilleur compromis · Translation – … »"""
    by_method = {}
    for method, variant in tags:
        variants = by_method.setdefault(method, [])
        if variant not in variants:
            variants.append(variant)
    return " · ".join(f"{method} – {' et '.join(variants)}" for method, variants in by_method.items())


def dedupe_routes(routes):
    unique = []
    by_key = {}
    for route in routes:
        key = route.pop("_key", None)
        if key and key in by_key:
            kept = by_key[key]
            kept["_tags"] += route.get("_tags", [])
            kept["includes_start"] = kept["includes_start"] or route["includes_start"]
            continue
        if key:
            by_key[key] = route
        unique.append(route)
    for i, route in enumerate(unique, start=1):
        route["id"] = f"route-{i}"
        tags = route.pop("_tags", None)
        if tags:
            route["variant"] = merged_variant_label(tags)
    return unique


def build_shape_routes(graph, drawing, distance_m, tolerance_ratio):
    # Dessin libre : la forme est celle tracée par l'utilisateur (voir custom_shape.py) ; sinon une forme prédéfinie.
    shape = "custom" if drawing.get("mode") == "custom" else drawing.get("shape", "heart")
    base_points = get_base_shape(shape, drawing.get("text", "P2I"), drawing.get("points"))
    label = SHAPE_LABELS.get(shape, shape.capitalize())
    return method_routes(graph, base_points, distance_m, tolerance_ratio, shape, label, "shape")


# Mode texte, trois façons de dessiner un mot de n lettres pour une distance D
# (renvoyées dans l'ordre 2), 3), 1) : « mot entier » vient en dernier, marqué `secondary`,
# et l'interface le range dans une section « autres propositions ») :
# 1) « Mot entier » : un itinéraire d'environ D km qui dessine tout le mot (trois méthodes de recherche) ;
# 2) « Lettres séparées » : n itinéraires d'environ D km, un par lettre (n fichiers GPX) ;
# 3) « Lettres reliées » : un itinéraire d'environ n x D km qui enchaîne les lettres de 2), reliées par
#    les plus courts chemins, chaque lettre parcourue dans le sens qui raccourcit le plus les liaisons.
def build_text_routes(graph, drawing, distance_m, tolerance_ratio):
    text = (drawing.get("text") or "P2I").upper()
    routes = []

    # 1) Mot entier (proposition secondaire, placée après les lettres)
    word_routes = method_routes(graph, get_base_shape("text", text), distance_m, tolerance_ratio,
                                "text", f"{text} — mot entier", "word")
    for route in word_routes:
        route["secondary"] = True

    # 2) Lettres séparées
    with timed("lettres séparées"):
        split_results = split_text_itineraries_full_distance(graph, text, distance_m, tolerance_ratio)
    letters_summary = []
    for item in split_results:
        m = item["metrics"]
        letters_summary.append({
            "letter": item["letter"],
            "distance_m": float(m.get("length_route", 0.0)),
            "length_gap_m": float(m.get("length_gap", 0.0)),
            "shape_error": float(m.get("shape_error", 0.0)),
        })
    n = max(len(split_results), 1)
    routes.append({
        "label": f"{text} — lettres séparées",
        "kind": "letters_separate",
        "variant": f"{len(split_results)} itinéraires distincts, un par lettre",
        "includes_start": False,
        "separate": True,
        "total_distance_m": sum(x["distance_m"] for x in letters_summary),
        "length_gap_m": sum(x["length_gap_m"] for x in letters_summary),
        "shape_error": sum(x["shape_error"] for x in letters_summary) / n,
        "turn_penalty": sum(float(r["metrics"].get("turn_penalty", 0.0)) for r in split_results) / n,
        "over_max_m": 0.0,
        "letters": letters_summary,
        "segments": [build_segment_from_candidate(graph, item, item["letter"]) for item in split_results],
    })

    # 3) Lettres reliées
    with timed("lettres reliées"):
        pieces, total_length = link_letter_routes(graph, split_results)
    if pieces:
        segments = []
        link_length = 0.0
        for piece in pieces:
            pts = graph.node_array[piece["node_path"]]
            length = float(sum(math.hypot(*(b - a)) for a, b in zip(pts[:-1], pts[1:])))
            if piece["kind"] == "link":
                link_length += length
            segments.append({
                "label": piece["letter"] or "liaison",
                "kind": piece["kind"],
                "points": route_points_xy_to_latlon(graph, pts),
                "distance_m": length,
                "node_path": [graph.node_ids[i] for i in piece["node_path"]],
                "anchors": piece["anchors"],
            })
        routes.append({
            "label": f"{text} — lettres reliées",
            "kind": "letters_linked",
            "variant": f"1 seul itinéraire, dont {link_length / 1000:.1f} km de liaisons entre les lettres",
            "includes_start": False,
            "total_distance_m": float(total_length),
            "length_gap_m": abs(float(total_length) - n * distance_m),
            "shape_error": sum(x["shape_error"] for x in letters_summary) / n,
            "turn_penalty": 0.0,
            "over_max_m": 0.0,
            "letters": letters_summary,
            "segments": segments,
        })

    return routes + word_routes


# Point d'entrée principal : calcule toutes les propositions sur un RoadGraph déjà construit.
# Il convertit la distance demandée, puis envoie la demande vers le mode forme ou le mode texte.
def plan_from_graph(graph, distance_km, drawing, tolerance_ratio=0.10) -> Dict[str, Any]:
    drawing = drawing or {}
    tolerance_ratio = 0.10 if tolerance_ratio is None else float(tolerance_ratio)
    distance_m = float(distance_km) * 1000.0

    mode = drawing.get("mode", "shape")

    with timed(f"calcul complet ({mode}, {distance_km} km, {len(graph.node_ids)} nœuds)"):
        routes = _build_routes(graph, drawing, distance_m, tolerance_ratio, mode)
    if mode == "text":
        summary = f"{len(routes)} proposition(s) pour le texte {(drawing.get('text') or 'P2I').upper()}."
    else:
        shape = "custom" if mode == "custom" else drawing.get("shape", "heart")
        summary = f"{len(routes)} proposition(s) pour la forme {SHAPE_LABELS.get(shape, shape)}."

    return {
        "summary": summary,
        "routes": routes,
    }


def _build_routes(graph, drawing, distance_m, tolerance_ratio, mode):
    if mode == "text":
        return dedupe_routes(build_text_routes(graph, drawing, distance_m, tolerance_ratio))
    return dedupe_routes(build_shape_routes(graph, drawing, distance_m, tolerance_ratio))
