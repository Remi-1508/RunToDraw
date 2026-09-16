"""Évaluation de la qualité d'un trajet candidat.

Un trajet est jugé sur quatre critères, combinés en un seul score
(`combined`) que la recherche cherche à minimiser :

- `shape_error` : à quel point le trajet ressemble à la forme cible,
- `length_gap` : écart entre la distance obtenue et la distance demandée,
- `turn_penalty` : présence de virages serrés,
- `over_max` : dépassement de la distance maximale tolérée.
"""

import numpy as np

from . import geometry as geo

# Poids relatifs des critères secondaires dans le score combiné. shape_error
# est en mètres et domine naturellement le score ; ces poids ramènent les
# autres critères à une échelle comparable.
_LENGTH_GAP_WEIGHT = 0.010
_TURN_PENALTY_WEIGHT = 0.080
_OVER_MAX_WEIGHT = 0.120

# Nombre de points utilisés pour comparer équitablement deux polylignes de
# longueurs différentes (voir geometry.resample_polyline).
_COMPARISON_SAMPLES = 180


def score_solution(route_points, target_points, desired_distance_m, max_allowed_m):
    """Note un trajet candidat par rapport à la forme cible et à la distance voulue."""
    length_target = geo.polyline_length(target_points)

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

    route_rs = geo.resample_polyline(route_points, n_samples=_COMPARISON_SAMPLES)
    target_rs = geo.resample_polyline(target_points, n_samples=_COMPARISON_SAMPLES)

    shape_error = float(np.mean(np.linalg.norm(route_rs - target_rs, axis=1)))
    length_route = geo.polyline_length(route_points)
    length_gap = abs(length_route - desired_distance_m)
    over_max = max(0.0, length_route - max_allowed_m)
    turn = geo.turn_penalty(route_points)
    combined = (
        shape_error
        + _LENGTH_GAP_WEIGHT * length_gap
        + _TURN_PENALTY_WEIGHT * turn
        + _OVER_MAX_WEIGHT * over_max
    )

    return {
        "shape_error": shape_error,
        "length_route": length_route,
        "length_target": length_target,
        "length_gap": length_gap,
        "over_max": over_max,
        "turn_penalty": turn,
        "combined": combined,
    }
