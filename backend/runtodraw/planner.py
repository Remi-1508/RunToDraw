"""Point d'entrée du moteur : transforme une requête de dessin en itinéraires.

Fait le lien entre l'API (un payload JSON) et le reste du moteur : reconstruit
le graphe routier, lance la recherche pour la forme ou le texte demandé, et
met les résultats en forme pour le frontend.
"""

from typing import Any, Dict

from . import geometry as geo
from .graph import RoadGraph
from .search import evaluate_method, split_text_itineraries_full_distance
from .shapes import get_base_shape

_METHODS = [("projection", "Projection"), ("translation", "Translation")]
_VARIANTS = [("closest_to_distance", "Distance la plus proche"), ("best_compromise", "Meilleur compromis")]


def _route_points_to_latlon(graph, route_points):
    """Reconvertit une polyligne x/y en points GPS pour l'affichage sur la carte."""
    out = []
    for p in route_points:
        lat, lon = geo.xy_to_latlon(float(p[0]), float(p[1]), graph.center_lat, graph.center_lon)
        out.append([lat, lon])
    return out


def _build_segment(graph, candidate, label):
    """Met en forme un segment d'itinéraire pour le frontend : label, points GPS, distance."""
    route_points = candidate.get("route_points")
    metrics = candidate.get("metrics", {})
    latlon_points = _route_points_to_latlon(graph, route_points) if route_points is not None else []

    return {
        "label": label,
        "points": latlon_points,
        "distance_m": float(metrics.get("length_route", 0.0)),
    }


def _build_variant_routes(graph, base_points, distance_m, tolerance_ratio, shape_name, route_label, segment_label):
    """Construit les 4 propositions (projection/translation x distance/compromis) pour une forme."""
    results = {
        method_name: evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, method_name)
        for method_name, _ in _METHODS
    }

    routes = []
    for method_name, method_label in _METHODS:
        for variant_name, variant_label in _VARIANTS:
            candidate = results[method_name][variant_name]
            metrics = candidate["metrics"]
            routes.append({
                "label": route_label,
                "variant": f"{method_label} - {variant_label}",
                "total_distance_m": float(metrics.get("length_route", 0.0)),
                "length_gap_m": float(metrics.get("length_gap", 0.0)),
                "shape_error": float(metrics.get("shape_error", 0.0)),
                "turn_penalty": float(metrics.get("turn_penalty", 0.0)),
                "over_max_m": float(metrics.get("over_max", 0.0)),
                "segments": [_build_segment(graph, candidate, segment_label)],
            })
    return routes


def build_shape_routes(graph, drawing, distance_m, tolerance_ratio):
    """Propositions d'itinéraires pour une forme classique (cœur, carré, cercle...)."""
    shape = drawing.get("shape", "heart")
    text = drawing.get("text", "P2I")
    base_points = get_base_shape(shape, text)
    label = shape.capitalize()

    routes = _build_variant_routes(
        graph, base_points, distance_m, tolerance_ratio, shape,
        route_label=label, segment_label=label,
    )
    for i, route in enumerate(routes, start=1):
        route["id"] = f"route-{i}"
    return routes


def build_text_routes(graph, drawing, distance_m, tolerance_ratio):
    """Propositions d'itinéraires pour un texte : lettres indépendantes + mot complet.

    Les deux modes sont volontairement proposés côte à côte : sur une même
    zone et une même distance, une lettre développée en entier peut donner un
    tracé plus fidèle que le mot compressé dans la distance demandée.
    L'utilisateur compare les deux et choisit celui qui lui convient.
    """
    text = (drawing.get("text") or "P2I").upper()

    split_results = split_text_itineraries_full_distance(graph, text, distance_m, tolerance_ratio)

    split_segments = []
    letters_summary = []
    total_distance = 0.0
    total_gap = 0.0
    total_shape_error = 0.0
    total_turn_penalty = 0.0

    for item in split_results:
        metrics = item["metrics"]
        split_segments.append(_build_segment(graph, item, item["letter"]))

        dist = float(metrics.get("length_route", 0.0))
        gap = float(metrics.get("length_gap", 0.0))
        shape_error = float(metrics.get("shape_error", 0.0))
        turn_penalty = float(metrics.get("turn_penalty", 0.0))

        total_distance += dist
        total_gap += gap
        total_shape_error += shape_error
        total_turn_penalty += turn_penalty

        letters_summary.append({
            "letter": item["letter"],
            "distance_m": dist,
            "length_gap_m": gap,
            "shape_error": shape_error,
        })

    split_route = {
        "label": f"Texte {text}",
        "variant": "Lettres indépendantes",
        "total_distance_m": total_distance,
        "length_gap_m": total_gap,
        "shape_error": total_shape_error / max(len(split_results), 1),
        "turn_penalty": total_turn_penalty / max(len(split_results), 1),
        "over_max_m": 0.0,
        "letters": letters_summary,
        "segments": split_segments,
    }

    base_points = get_base_shape("text", text)
    whole_word_routes = _build_variant_routes(
        graph, base_points, distance_m, tolerance_ratio, "text",
        route_label=f"Mot complet {text}", segment_label=text,
    )

    routes = [split_route] + whole_word_routes
    for i, route in enumerate(routes, start=1):
        route["id"] = f"route-{i}"
    return routes


def plan_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Point d'entrée principal appelé par l'API : calcule les itinéraires demandés."""
    graph_payload = payload.get("graph_payload")
    distance_km = float(payload.get("distance_km", 0.0))
    drawing = payload.get("drawing", {}) or {}
    tolerance_ratio = float(payload.get("tolerance_ratio", 0.10))

    if not graph_payload:
        raise ValueError("graph_payload manquant")

    if "meta" not in graph_payload or "nodes" not in graph_payload or "edges" not in graph_payload:
        raise ValueError("graph_payload invalide : meta/nodes/edges requis")

    graph = RoadGraph(graph_payload)
    distance_m = distance_km * 1000.0

    mode = drawing.get("mode", "shape")

    if mode == "text":
        routes = build_text_routes(graph, drawing, distance_m, tolerance_ratio)
        summary = f"{len(routes)} proposition(s) calculée(s) pour le texte {drawing.get('text', 'P2I').upper()}."
    else:
        routes = build_shape_routes(graph, drawing, distance_m, tolerance_ratio)
        summary = f"{len(routes)} proposition(s) calculée(s) pour la forme {drawing.get('shape', 'heart')}."

    return {
        "summary": summary,
        "routes": routes,
    }
