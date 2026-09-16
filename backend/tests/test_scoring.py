"""Tests unitaires du module scoring (score_solution)."""
import numpy as np
import pytest

from runtodraw import scoring

SQUARE_ROUTE = np.array([[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]], dtype=float)


def test_route_too_short_returns_infinite_penalties():
    result = scoring.score_solution([[0, 0]], SQUARE_ROUTE, desired_distance_m=400.0, max_allowed_m=440.0)
    assert result["shape_error"] == float("inf")
    assert result["turn_penalty"] == float("inf")
    assert result["combined"] == float("inf")
    assert result["length_route"] == 0.0
    assert result["length_gap"] == 400.0
    assert result["over_max"] == 440.0


def test_identical_route_and_target_has_zero_shape_error():
    result = scoring.score_solution(SQUARE_ROUTE, SQUARE_ROUTE, desired_distance_m=400.0, max_allowed_m=440.0)
    assert result["shape_error"] == pytest.approx(0.0, abs=1e-9)
    assert result["length_route"] == pytest.approx(400.0)
    assert result["length_gap"] == pytest.approx(0.0)
    assert result["over_max"] == 0.0


def test_over_max_is_only_the_excess_beyond_the_limit():
    result = scoring.score_solution(SQUARE_ROUTE, SQUARE_ROUTE, desired_distance_m=400.0, max_allowed_m=350.0)
    assert result["over_max"] == pytest.approx(50.0)


def test_combined_score_matches_the_weighted_sum():
    result = scoring.score_solution(SQUARE_ROUTE, SQUARE_ROUTE, desired_distance_m=380.0, max_allowed_m=390.0)
    expected = (
        result["shape_error"]
        + 0.010 * result["length_gap"]
        + 0.080 * result["turn_penalty"]
        + 0.120 * result["over_max"]
    )
    assert result["combined"] == pytest.approx(expected)
