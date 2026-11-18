"""Évaluation d'un trajet : ressemblance avec la forme (distance de Chamfer), écart de distance,
fluidité (virages) et dépassement de la distance maximale."""
import math

from scipy.spatial import cKDTree
import numpy as np

from runtodraw.geometry import path_turn_penalty, polyline_length, resample_polyline


# EN:
# Shape distance (in meters) between the route and the target drawing.
# Former metric: both polylines were resampled to 180 points and compared point by point, in order.
# A smooth, rounded route scored well even when it "planed off" the details that make a shape
# recognizable (the dip and the tip of a heart, the points of a star), because those details are a
# small part of the outline. With a wider search (every orientation), the optimizer exploited this.
# New metric, symmetric Chamfer distance + a high percentile:
# - for each point of the drawing, the distance to the nearest point of the route (d_target),
# - for each point of the route, the distance to the nearest point of the drawing (d_route),
# - shape_distance = (mean(d_target) + mean(d_route)) / 2 + 0.5 * percentile_90(d_target).
# The two means measure the overall fit in both directions (a detour away from the drawing is
# penalized by d_route); the 90th percentile makes a missed detail costly. Both polylines are
# densified every ~10 m and queried with KD-trees: O(n log n), about a millisecond per candidate.
#
# FR:
# Distance de forme (en mètres) entre le trajet et le dessin cible.
# Ancienne mesure : les deux polylignes étaient rééchantillonnées en 180 points et comparées point à point,
# dans l'ordre. Un trajet lisse et arrondi obtenait une bonne note même s'il « rabotait » les détails qui
# rendent une forme reconnaissable (le creux et la pointe du cœur, les branches de l'étoile), car ces
# détails ne représentent qu'une petite partie du contour. Avec une recherche plus large (toutes les
# orientations), l'optimisation exploitait ce défaut.
# Nouvelle mesure, distance de Chamfer symétrique + un centile élevé :
# - pour chaque point du dessin, la distance au point le plus proche du trajet (d_cible),
# - pour chaque point du trajet, la distance au point le plus proche du dessin (d_trajet),
# - distance_forme = (moyenne(d_cible) + moyenne(d_trajet)) / 2 + 0,5 × centile_90(d_cible).
# Les deux moyennes mesurent l'accord global dans les deux sens (un détour loin du dessin est pénalisé
# par d_trajet) ; le 90e centile rend coûteux un détail manqué. Les deux polylignes sont densifiées tous
# les ~10 m et interrogées par KD-tree : O(n log n), environ une milliseconde par candidat.
SHAPE_SAMPLE_STEP_M = 10.0


def _densify(points, step_m=SHAPE_SAMPLE_STEP_M):
    n = int(math.ceil(polyline_length(points) / step_m)) + 1
    return resample_polyline(points, n_samples=max(n, 2))


def shape_distance_m(route_points, target_points):
    route = _densify(route_points)
    target = _densify(target_points)
    d_target, _ = cKDTree(route).query(target)
    d_route, _ = cKDTree(target).query(route)
    return float(0.5 * (d_target.mean() + d_route.mean()) + 0.5 * np.percentile(d_target, 90))


# EN: `route_length_m` is the real length of the path on the roads. When it is not given, we fall
# back to the length of `route_points` (which may be a simplified polyline, hence slightly shorter).
# FR: `route_length_m` est la vraie longueur du trajet sur les routes. Si elle n'est pas fournie, on
# prend la longueur de `route_points` (qui peut être une polyligne simplifiée, donc un peu plus courte).
def score_solution(route_points, target_points, desired_distance_m, max_allowed_m, route_length_m=None):
    length_target = polyline_length(target_points)

    if len(route_points) < 2:
        return {
            "shape_error": float("inf"),
            "length_route": 0.0,
            "length_target": length_target,
            "length_gap": desired_distance_m,
            "over_max": max_allowed_m,
            "turn_penalty": float("inf"),
            "combined": float("inf"),
        }

    shape_error = shape_distance_m(route_points, target_points)
    length_route = polyline_length(route_points) if route_length_m is None else float(route_length_m)
    length_gap = abs(length_route - desired_distance_m)
    over = max(0.0, length_route - max_allowed_m)
    turn = path_turn_penalty(route_points)
    combined = shape_error + 0.010 * length_gap + 0.080 * turn + 0.120 * over

    return {
        "shape_error": shape_error,
        "length_route": length_route,
        "length_target": length_target,
        "length_gap": length_gap,
        "over_max": over,
        "turn_penalty": turn,
        "combined": combined,
    }
