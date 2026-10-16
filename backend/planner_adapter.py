import math
from typing import Any, Dict, List

from shape_route_experiments_v16 import (
    RoadGraph,
    evaluate_method,
    evaluate_start_method,
    get_base_shape,
    link_letter_routes,
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
    metrics = candidate.get("metrics", {})

    # EN: We send the full path, node by node, so that the drawn route and the GPX export follow
    # the streets exactly. (The simplified polyline is only used internally for scoring.)
    # FR: On envoie le chemin complet, nœud par nœud, pour que le tracé affiché et l'export GPX
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
    }


SHAPE_LABELS = {
    "heart": "Cœur",
    "square": "Carré",
    "circle": "Rond",
    "star": "Étoile",
    "infinity": "Infini",
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


# EN: Runs the three search methods on one drawing (shape or whole word) and formats every
# (method, variant) result as a route proposal.
# FR: Lance les trois méthodes de recherche sur un dessin (forme ou mot entier) et met en forme
# chaque résultat (méthode, variante) comme une proposition d'itinéraire.
def method_routes(graph, base_points, distance_m, tolerance_ratio, shape_name, label, kind):
    results = {
        "projection": evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, "projection"),
        "translation": evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, "translation"),
        "start": evaluate_start_method(graph, base_points, distance_m, tolerance_ratio, shape_name),
    }
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


# EN: Removes duplicate proposals. The same route is often found by several methods or variants
# (e.g. the best translation is the centered one, so it equals the projection). Identical routes
# (same nodes, in the same order) are merged and their labels are combined.
# FR: Supprime les propositions en double. Le même trajet est souvent trouvé par plusieurs méthodes ou
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
    shape = drawing.get("shape", "heart")
    base_points = get_base_shape(shape, drawing.get("text", "P2I"))
    label = SHAPE_LABELS.get(shape, shape.capitalize())
    return method_routes(graph, base_points, distance_m, tolerance_ratio, shape, label, "shape")


# EN: Text mode, three ways to draw a word of n letters for a distance D:
# 1) "Whole word": one route of about D km drawing the whole word (three search methods);
# 2) "Separate letters": n routes of about D km each, one per letter (n GPX files);
# 3) "Linked letters": one route of about n x D km that draws the letters of 2) one after the other,
#    joined by the shortest paths, each letter run in the direction that keeps the links shortest.
# FR: Mode texte, trois façons de dessiner un mot de n lettres pour une distance D :
# 1) « Mot entier » : un itinéraire d'environ D km qui dessine tout le mot (trois méthodes de recherche) ;
# 2) « Lettres séparées » : n itinéraires d'environ D km, un par lettre (n fichiers GPX) ;
# 3) « Lettres reliées » : un itinéraire d'environ n x D km qui enchaîne les lettres de 2), reliées par
#    les plus courts chemins, chaque lettre parcourue dans le sens qui raccourcit le plus les liaisons.
def build_text_routes(graph, drawing, distance_m, tolerance_ratio):
    text = (drawing.get("text") or "P2I").upper()
    routes = []

    # 1) Mot entier
    routes += method_routes(graph, get_base_shape("text", text), distance_m, tolerance_ratio,
                            "text", f"{text} — mot entier", "word")

    # 2) Lettres séparées
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

    return routes


# EN: Main entry point: computes all route proposals on an already built RoadGraph.
# It converts the requested distance, then sends the request either to shape mode or text mode.
# FR: Point d'entrée principal : calcule toutes les propositions sur un RoadGraph déjà construit.
# Il convertit la distance demandée, puis envoie la demande vers le mode forme ou le mode texte.
def plan_from_graph(graph, distance_km, drawing, tolerance_ratio=0.10) -> Dict[str, Any]:
    drawing = drawing or {}
    tolerance_ratio = 0.10 if tolerance_ratio is None else float(tolerance_ratio)
    distance_m = float(distance_km) * 1000.0

    mode = drawing.get("mode", "shape")

    if mode == "text":
        routes = dedupe_routes(build_text_routes(graph, drawing, distance_m, tolerance_ratio))
        summary = f"{len(routes)} proposition(s) pour le texte {(drawing.get('text') or 'P2I').upper()}."
    else:
        routes = dedupe_routes(build_shape_routes(graph, drawing, distance_m, tolerance_ratio))
        shape = drawing.get("shape", "heart")
        summary = f"{len(routes)} proposition(s) pour la forme {SHAPE_LABELS.get(shape, shape)}."

    return {
        "summary": summary,
        "routes": routes,
    }


# EN: Former entry point, still used when the whole graph is sent in the request
# (and by the experiment scripts). It validates the payload and rebuilds the graph.
# FR: Ancien point d'entrée, toujours utilisé quand le graphe complet est envoyé dans la requête
# (et par les scripts d'expérimentation). Il vérifie le contenu reçu et reconstruit le graphe.
def plan_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    graph_payload = payload.get("graph_payload")

    if not graph_payload:
        raise ValueError("graph_payload manquant")

    if "meta" not in graph_payload or "nodes" not in graph_payload or "edges" not in graph_payload:
        raise ValueError("graph_payload invalide : meta/nodes/edges requis")

    return plan_from_graph(
        RoadGraph(graph_payload),
        float(payload.get("distance_km", 0.0)),
        payload.get("drawing", {}) or {},
        payload.get("tolerance_ratio", 0.10),
    )
