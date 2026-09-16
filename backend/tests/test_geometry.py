"""Tests unitaires du module geometry."""
import numpy as np
import pytest

from runtodraw import geometry as geo

SQUARE = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], dtype=float)


def test_latlon_xy_roundtrip():
    x, y = geo.latlon_to_xy(44.85, -0.57, 44.84, -0.58)
    lat, lon = geo.xy_to_latlon(x, y, 44.84, -0.58)
    assert lat == pytest.approx(44.85)
    assert lon == pytest.approx(-0.57)


def test_projection_matches_haversine_at_running_scale():
    # Sur ~7 km, la projection locale reste précise à mieux que 0,1 %.
    x, y = geo.latlon_to_xy(44.90, -0.52, 44.84, -0.58)
    assert np.hypot(x, y) == pytest.approx(geo.haversine_m(44.84, -0.58, 44.90, -0.52), rel=1e-3)


def test_polyline_length():
    assert geo.polyline_length(SQUARE) == pytest.approx(40.0)
    assert geo.polyline_length([[1, 1]]) == 0.0


def test_clean_polyline_removes_consecutive_duplicates():
    pts = [[0, 0], [0, 0], [1, 0], [1, 0], [0, 0]]
    assert geo.clean_polyline(pts).tolist() == [[0, 0], [1, 0], [0, 0]]


def test_resample_keeps_endpoints_and_regular_spacing():
    out = geo.resample_polyline(SQUARE, n_samples=41)
    assert len(out) == 41
    assert out[0].tolist() == [0, 0] and out[-1].tolist() == [0, 0]
    assert np.allclose(np.linalg.norm(np.diff(out, axis=0), axis=1), 1.0)


def test_rotate_quarter_turn():
    assert np.allclose(geo.rotate_points([[1, 0]], 90), [[0, 1]])


def test_fit_points_sets_size_and_center():
    out = geo.fit_points(SQUARE, center=(100, 200), size_m=50)
    assert np.allclose(out.min(axis=0), [75, 175])
    assert np.allclose(out.max(axis=0), [125, 225])


def test_simplify_removes_collinear_points():
    line = [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1]]
    assert geo.simplify_path_points(line).tolist() == [[0, 0], [3, 0], [3, 1]]


def test_turn_penalty():
    assert geo.turn_penalty([[0, 0], [1, 0], [2, 0]]) == 0.0
    # Un virage à 90° coûte 90 - 35 = 55.
    assert geo.turn_penalty([[0, 0], [1, 0], [1, 1]]) == pytest.approx(55.0)
