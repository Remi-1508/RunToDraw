"""Point d'entrée du moteur : transforme une requête de dessin en itinéraires.

Fait le lien entre l'API (un payload JSON) et le reste du moteur : reconstruit
le graphe routier, lance la recherche pour la forme ou le texte demandé, et
met les résultats en forme pour le frontend.
"""

import threading
import time
from typing import Any, Dict

from . import geometry as geo
from . import parallel
from .graph import RoadGraph
from .search import (
    count_split_text_candidates,
    count_variant_candidates,
    evaluate_method,
    split_text_itineraries_full_distance,
)
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


def _build_variant_routes(graph, base_points, distance_m, tolerance_ratio, shape_name, route_label, segment_label,
                           executor=None, on_progress=None):
    """Construit les 4 propositions (projection/translation x distance/compromis) pour une forme."""
    results = {
        method_name: evaluate_method(graph, base_points, distance_m, tolerance_ratio, shape_name, method_name,
                                      executor=executor, on_progress=on_progress)
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


def build_shape_routes(graph, drawing, distance_m, tolerance_ratio, executor=None, on_progress=None):
    """Propositions d'itinéraires pour une forme classique (cœur, carré, cercle...)."""
    shape = drawing.get("shape", "heart")
    text = drawing.get("text", "P2I")
    base_points = get_base_shape(shape, text)
    label = shape.capitalize()

    routes = _build_variant_routes(
        graph, base_points, distance_m, tolerance_ratio, shape,
        route_label=label, segment_label=label, executor=executor, on_progress=on_progress,
    )
    for i, route in enumerate(routes, start=1):
        route["id"] = f"route-{i}"
    return routes


def build_text_routes(graph, drawing, distance_m, tolerance_ratio, executor=None, on_progress=None):
    """Propositions d'itinéraires pour un texte : lettres indépendantes + mot complet.

    Les deux modes sont volontairement proposés côte à côte : sur une même
    zone et une même distance, une lettre développée en entier peut donner un
    tracé plus fidèle que le mot compressé dans la distance demandée.
    L'utilisateur compare les deux et choisit celui qui lui convient.
    """
    text = (drawing.get("text") or "P2I").upper()

    split_results = split_text_itineraries_full_distance(
        graph, text, distance_m, tolerance_ratio, executor=executor, on_progress=on_progress
    )

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
        route_label=f"Mot complet {text}", segment_label=text, executor=executor, on_progress=on_progress,
    )

    routes = [split_route] + whole_word_routes
    for i, route in enumerate(routes, start=1):
        route["id"] = f"route-{i}"
    return routes


def _make_progress_reporter(total_candidates, progress_callback):
    """Convertit des incréments "un candidat de plus" en une fraction 0..1.

    Le total est connu à l'avance (voir count_variant_candidates /
    count_split_text_candidates), donc la progression reflète le travail
    réellement fait, pas une barre de chargement simulée par un minuteur.

    Les candidats sont évalués par plusieurs threads (voir parallel.py) : le
    compteur et l'appel du callback sont protégés par un verrou pour éviter
    de perdre des incréments, et pour garantir que la progression rapportée
    est toujours croissante.
    """
    if progress_callback is None:
        return None
    done = {"n": 0}
    total = max(total_candidates, 1)
    lock = threading.Lock()

    def on_progress():
        with lock:
            done["n"] += 1
            progress_callback(min(done["n"] / total, 1.0))

    return on_progress


def plan_from_payload(payload: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
    """Point d'entrée principal appelé par l'API : calcule les itinéraires demandés.

    `progress_callback(fraction)`, si fourni, est appelé au fil de la
    recherche avec une fraction croissante de 0.0 à 1.0 (voir jobs.py, qui
    l'utilise pour exposer une vraie progression via polling).
    """
    start = time.perf_counter()

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
        text = (drawing.get("text") or "P2I").upper()
        text_base_points = get_base_shape("text", text)
        total_candidates = (
            count_split_text_candidates(text)
            + count_variant_candidates(graph, text_base_points, distance_m, "text")
        )
    else:
        shape = drawing.get("shape", "heart")
        shape_base_points = get_base_shape(shape, drawing.get("text", "P2I"))
        total_candidates = count_variant_candidates(graph, shape_base_points, distance_m, shape)

    on_progress = _make_progress_reporter(total_candidates, progress_callback)

    with parallel.make_executor() as executor:
        if mode == "text":
            routes = build_text_routes(graph, drawing, distance_m, tolerance_ratio, executor=executor,
                                        on_progress=on_progress)
            summary = f"{len(routes)} proposition(s) calculée(s) pour le texte {drawing.get('text', 'P2I').upper()}."
        else:
            routes = build_shape_routes(graph, drawing, distance_m, tolerance_ratio, executor=executor,
                                         on_progress=on_progress)
            summary = f"{len(routes)} proposition(s) calculée(s) pour la forme {drawing.get('shape', 'heart')}."

    if progress_callback:
        progress_callback(1.0)

    return {
        "summary": summary,
        "routes": routes,
        "duration_s": time.perf_counter() - start,
    }
