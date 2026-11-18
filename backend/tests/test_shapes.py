"""Formes de base et dessin libre."""
import numpy as np
import pytest

from runtodraw.custom_shape import MAX_SHAPE_POINTS, prepare_custom_shape, simplify_rdp
from runtodraw.search import MAX_TILT_DEG, ORIENTATION_RULES, search_angles
from runtodraw.shapes import get_base_shape
from runtodraw.validation import SHAPES

NEW_SHAPES = ["triangle", "diamond", "cross", "arrow", "house", "lightning", "crescent", "drop"]


@pytest.mark.parametrize("name", list(SHAPES))
def test_every_shape_is_a_closed_non_degenerate_outline(name):
    pts = get_base_shape(name, "")
    assert pts.shape[1] == 2 and len(pts) >= 4
    assert np.allclose(pts[0], pts[-1]), "contour fermé : le départ est aussi l'arrivée"
    assert np.ptp(pts[:, 0]) > 0.2 and np.ptp(pts[:, 1]) > 0.2


def test_new_shapes_are_all_registered():
    assert all(name in SHAPES for name in NEW_SHAPES)


def test_upright_shapes_are_tilted_only_a_little():
    class FakeGraph:
        _dominant_angle = 33.0

    for name, limit in MAX_TILT_DEG.items():
        angles = search_angles(FakeGraph, name)
        assert max(abs(a) for a in angles) == pytest.approx(limit)
        assert 0.0 in [round(a, 6) for a in angles] or len(angles) % 2 == 0
    # une flèche peut pointer n'importe où
    assert len(search_angles(FakeGraph, "arrow")) == 36
    assert "custom" in ORIENTATION_RULES


def _canvas_circle(n=60, radius=100.0, cx=200.0, cy=150.0, closed=False):
    t = np.linspace(0, 2 * np.pi, n, endpoint=closed)
    return np.column_stack([cx + radius * np.cos(t), cy + radius * np.sin(t)]).tolist()


def test_custom_drawing_is_flipped_centered_and_closed():
    # Triangle pointe en haut sur un canvas (y vers le bas : le sommet a le plus petit y).
    raw = [[100, 200], [200, 200], [150, 100], [101, 199]]
    pts = np.array(prepare_custom_shape(raw))
    assert np.allclose(pts[0], pts[-1])                       # presque refermé -> refermé
    apex = pts[np.argmax(pts[:, 1])]
    assert apex[0] == pytest.approx(0.0, abs=0.02) and apex[1] > 0   # le sommet est en haut sur la carte (y vers le haut)
    assert pts.min(axis=0)[0] == pytest.approx(-pts.max(axis=0)[0], abs=1e-9)  # centré


@pytest.mark.parametrize("scale", [1.0, 0.01, 300.0])
def test_custom_drawing_is_normalized_whatever_its_pixel_size(scale):
    """Régression : un dessin en pixels (centaines d'unités) était traité comme un contour 200 fois trop long,
    et tracé minuscule. Quelle que soit l'échelle, la plus grande dimension doit valoir 1."""
    raw = (np.array([[0, 0], [200, 10], [220, 150], [100, 190], [10, 120], [0, 0]]) * scale).tolist()
    pts = np.array(prepare_custom_shape(raw))
    assert max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1])) == pytest.approx(1.0)


def test_custom_drawing_is_simplified():
    pts = prepare_custom_shape(_canvas_circle(n=900, closed=True))
    assert 8 <= len(pts) <= MAX_SHAPE_POINTS


def test_open_stroke_stays_open():
    raw = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 200], [100, 200]]   # zigzag en S
    pts = np.array(prepare_custom_shape(raw))
    assert not np.allclose(pts[0], pts[-1])


@pytest.mark.parametrize("raw, fragment", [
    ([[5, 5]], "trop court"),
    ([[5, 5], [5, 5], [5, 5]], "trop court"),
    ([[0, 0], [1e-7, 0], [2e-7, 0]], "trop petit"),
    ([[0, 0], [float("nan"), 3], [4, 5]], "invalides"),
    ([[0, 0], [1e9, 3], [4, 5]], "invalides"),
])
def test_unusable_drawings_are_rejected_with_a_message(raw, fragment):
    with pytest.raises(ValueError, match=fragment):
        prepare_custom_shape(raw)


def test_rdp_keeps_corners_and_drops_collinear_points():
    pts = [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3]]
    assert simplify_rdp(pts, 0.01).tolist() == [[0, 0], [3, 0], [3, 3]]


def test_custom_shape_goes_through_the_whole_engine():
    """Un dessin libre produit des propositions sur un réseau routier synthétique."""
    from runtodraw.planner import plan_from_graph
    from runtodraw.road_graph import RoadGraph
    from tests.test_road_graph import random_road_graph

    pts = prepare_custom_shape([[0, 100], [100, 100], [100, 0], [50, -40], [0, 0], [0, 100]])
    graph = RoadGraph(random_road_graph(7, n_side=45, step=70.0, oneway_ratio=0.0))
    plan = plan_from_graph(graph, 4.0, {"mode": "custom", "points": pts})
    assert plan["routes"], "au moins une proposition"
    assert "Mon dessin" in plan["summary"] or plan["routes"][0]["label"] == "Mon dessin"


def test_custom_drawing_in_pixels_gets_the_requested_distance():
    """Régression : un dessin de 300 px de large donnait un parcours de 0,7 km au lieu de la distance demandée."""
    from runtodraw.planner import plan_from_graph
    from runtodraw.road_graph import RoadGraph
    from tests.test_road_graph import random_road_graph

    raw = [[40, 160], [150, 150], [250, 170], [260, 230], [150, 250], [60, 240], [30, 200], [40, 160]]
    graph = RoadGraph(random_road_graph(7, n_side=45, step=70.0, oneway_ratio=0.0))
    plan = plan_from_graph(graph, 4.0, {"mode": "custom", "points": prepare_custom_shape(raw)})
    best = min(plan["routes"], key=lambda r: abs(r["total_distance_m"] - 4000.0))
    assert 2800 < best["total_distance_m"] < 5200


@pytest.mark.parametrize("name", NEW_SHAPES)
def test_new_shapes_go_through_the_whole_engine(name):
    from runtodraw.planner import plan_from_graph
    from runtodraw.road_graph import RoadGraph
    from tests.test_road_graph import random_road_graph

    graph = RoadGraph(random_road_graph(7, n_side=45, step=70.0, oneway_ratio=0.0))
    plan = plan_from_graph(graph, 4.0, {"mode": "shape", "shape": name})
    assert plan["routes"]
    assert all(r["total_distance_m"] > 500 for r in plan["routes"])
