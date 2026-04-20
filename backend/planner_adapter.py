import math
from typing import Any, Dict, List

from shape_route_experiments_v16 import (
    RoadGraph,
    evaluate_method,
    get_base_shape,
    split_text_itineraries_full_distance,
)


# EN: The route generator works internally in a local x/y coordinate system.
# This helper converts one point back to latitude/longitude so that the frontend
# can display the route on the real map.
# FR: Le générateur d’itinéraires travaille en interne avec un repère local x/y.
# Cette fonction reconvertit un point en latitude/longitude pour que le frontend
# puisse afficher le trajet sur la vraie carte.
def xy_to_latlon_m(x, y, lat0, lon0):
    r = 6371000.0
    lat = lat0 + math.degrees(y / r)
    lon = lon0 + math.degrees(x / (r * math.cos(math.radians(lat0))))
    return lat, lon


# EN: A candidate route is first computed in local coordinates.
# This function converts the whole polyline back to GPS points.
# FR: Un trajet candidat est d’abord calculé en coordonnées locales.
# Cette fonction reconvertit toute la polyligne en points GPS.
def route_points_xy_to_latlon(graph, route_points):
    out = []
    for p in route_points:
        lat, lon = xy_to_latlon_m(float(p[0]), float(p[1]), graph.center_lat, graph.center_lon)
        out.append([lat, lon])
    return out


# EN: This formats one route segment in the structure expected by the frontend.
# It keeps a label, the GPS points, and the measured distance.
# FR: Cette fonction met en forme un segment d’itinéraire dans la structure attendue
# par le frontend. On garde un label, les points GPS et la distance mesurée.
def build_segment_from_candidate(graph, candidate, label):
    route_points = candidate.get("route_points")
    metrics = candidate.get("metrics", {})

    latlon_points = route_points_xy_to_latlon(graph, route_points) if route_points is not None else []

    return {
        "label": label,
        "points": latlon_points,
        "distance_m": float(metrics.get("length_route", 0.0)),
    }


# EN: This builds all route proposals for a classic shape request
# such as a heart, a square, a circle, etc.
# We keep the four main variants returned by the search:
# projection/translation and closest distance/best compromise.
# FR: Cette fonction construit toutes les propositions pour une forme classique
# comme un cœur, un carré, un cercle, etc.
# On garde les quatre variantes principales renvoyées par la recherche :
# projection/translation et distance la plus proche/meilleur compromis.
def build_shape_routes(graph, drawing, distance_m, tolerance_ratio):
    shape = drawing.get("shape", "heart")
    text = drawing.get("text", "P2I")

    base_points = get_base_shape(shape, text)

    results = {
        "projection": evaluate_method(
            graph,
            base_points,
            distance_m,
            tolerance_ratio,
            shape,
            "projection",
        ),
        "translation": evaluate_method(
            graph,
            base_points,
            distance_m,
            tolerance_ratio,
            shape,
            "translation",
        ),
    }

    routes = []
    route_id = 1

    for method_name, method_label in [
        ("projection", "Projection"),
        ("translation", "Translation"),
    ]:
        for variant_name, variant_label in [
            ("closest_to_distance", "Distance la plus proche"),
            ("best_compromise", "Meilleur compromis"),
        ]:
            candidate = results[method_name][variant_name]
            metrics = candidate["metrics"]

            routes.append(
                {
                    "id": f"route-{route_id}",
                    "label": shape.capitalize(),
                    "variant": f"{method_label} - {variant_label}",
                    "total_distance_m": float(metrics.get("length_route", 0.0)),
                    "length_gap_m": float(metrics.get("length_gap", 0.0)),
                    "shape_error": float(metrics.get("shape_error", 0.0)),
                    "turn_penalty": float(metrics.get("turn_penalty", 0.0)),
                    "over_max_m": float(metrics.get("over_max", 0.0)),
                    "segments": [
                        build_segment_from_candidate(graph, candidate, shape.capitalize())
                    ],
                }
            )
            route_id += 1

    return routes


# EN: Text mode is handled in two ways in V16:
# 1) each letter is searched independently with the full requested distance,
# 2) the whole word is also tested as one global shape.
# This gives the user several types of route proposals.
# FR: Le mode texte est géré de deux façons dans V16 :
# 1) chaque lettre est cherchée indépendamment avec la distance complète demandée,
# 2) le mot complet est aussi testé comme une seule forme globale.
# Cela permet de proposer plusieurs types d’itinéraires à l’utilisateur.
def build_text_routes(graph, drawing, distance_m, tolerance_ratio):
    text = (drawing.get("text") or "P2I").upper()

    routes = []
    route_id = 1

    # EN: First, we compute the "independent letters" mode.
    # In V16, each letter receives the full requested distance.
    # FR: On calcule d’abord le mode "lettres indépendantes".
    # En V16, chaque lettre reçoit la distance complète demandée.
    split_results = split_text_itineraries_full_distance(
        graph,
        text,
        distance_m,
        tolerance_ratio,
    )

    split_segments = []
    letters_summary = []
    total_distance = 0.0
    total_gap = 0.0
    total_shape_error = 0.0
    total_turn_penalty = 0.0

    for item in split_results:
        metrics = item["metrics"]
        seg = build_segment_from_candidate(graph, item, item["letter"])
        split_segments.append(seg)

        dist = float(metrics.get("length_route", 0.0))
        gap = float(metrics.get("length_gap", 0.0))
        shape_error = float(metrics.get("shape_error", 0.0))
        turn_penalty = float(metrics.get("turn_penalty", 0.0))

        total_distance += dist
        total_gap += gap
        total_shape_error += shape_error
        total_turn_penalty += turn_penalty

        letters_summary.append(
            {
                "letter": item["letter"],
                "distance_m": dist,
                "length_gap_m": gap,
                "shape_error": shape_error,
            }
        )

    routes.append(
        {
            "id": f"route-{route_id}",
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
    )
    route_id += 1

    # EN: Then we also test the full word as one shape.
    # We keep the same four search variants as for normal shapes.
    # FR: Ensuite, on teste aussi le mot complet comme une seule forme.
    # On garde les mêmes quatre variantes de recherche que pour les formes classiques.
    base_points = get_base_shape("text", text)
    results = {
        "projection": evaluate_method(
            graph,
            base_points,
            distance_m,
            tolerance_ratio,
            "text",
            "projection",
        ),
        "translation": evaluate_method(
            graph,
            base_points,
            distance_m,
            tolerance_ratio,
            "text",
            "translation",
        ),
    }

    for method_name, method_label in [
        ("projection", "Projection"),
        ("translation", "Translation"),
    ]:
        for variant_name, variant_label in [
            ("closest_to_distance", "Distance la plus proche"),
            ("best_compromise", "Meilleur compromis"),
        ]:
            candidate = results[method_name][variant_name]
            metrics = candidate["metrics"]

            routes.append(
                {
                    "id": f"route-{route_id}",
                    "label": f"Mot complet {text}",
                    "variant": f"{method_label} - {variant_label}",
                    "total_distance_m": float(metrics.get("length_route", 0.0)),
                    "length_gap_m": float(metrics.get("length_gap", 0.0)),
                    "shape_error": float(metrics.get("shape_error", 0.0)),
                    "turn_penalty": float(metrics.get("turn_penalty", 0.0)),
                    "over_max_m": float(metrics.get("over_max", 0.0)),
                    "segments": [
                        build_segment_from_candidate(graph, candidate, text)
                    ],
                }
            )
            route_id += 1

    return routes


# EN: This is the main entry point called by the API.
# It validates the payload, rebuilds the graph, converts the requested distance,
# then sends the request either to shape mode or text mode.
# In the end, it returns a simple summary and a list of formatted route proposals.
# FR: C’est le point d’entrée principal appelé par l’API.
# Cette fonction vérifie le contenu reçu, reconstruit le graphe, convertit la distance demandée,
# puis envoie la demande soit vers le mode forme, soit vers le mode texte.
# À la fin, elle renvoie un résumé simple et une liste de propositions d’itinéraires déjà formatées.
def plan_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
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