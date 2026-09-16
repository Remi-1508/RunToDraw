"""Tests unitaires du module graph (RoadGraph, nearest_node, shortest_path)."""
import math

import numpy as np
import pytest

from runtodraw import geometry as geo
from runtodraw.graph import RoadGraph


def _latlon_from_xy(x, y):
    # lat0 = lon0 = 0 : simplifie la conversion inverse pour construire les fixtures.
    lon = math.degrees(x / geo.EARTH_RADIUS_M)
    lat = math.degrees(y / geo.EARTH_RADIUS_M)
    return lat, lon


def _make_payload(node_xy, edges):
    nodes = []
    for nid, (x, y) in node_xy.items():
        lat, lon = _latlon_from_xy(x, y)
        nodes.append({"id": nid, "lat": lat, "lon": lon})
    return {
        "meta": {"center": [0.0, 0.0]},
        "nodes": nodes,
        "edges": edges,
    }


def _grid_graph(spacing=100.0):
    """Grille 3x3, id = i*3+j, x = i*spacing, y = j*spacing."""
    node_xy = {i * 3 + j: (i * spacing, j * spacing) for i in range(3) for j in range(3)}
    edges = []
    for i in range(3):
        for j in range(3):
            nid = i * 3 + j
            if i + 1 < 3:
                edges.append({"from": nid, "to": (i + 1) * 3 + j, "length_m": spacing})
            if j + 1 < 3:
                edges.append({"from": nid, "to": i * 3 + (j + 1), "length_m": spacing})
    return RoadGraph(_make_payload(node_xy, edges))


def test_shortest_path_on_grid_follows_manhattan_distance():
    graph = _grid_graph(spacing=100.0)
    path, dist = graph.shortest_path(0, 8)  # coin (0,0) -> coin (200,200)
    assert dist == pytest.approx(400.0)
    assert path[0] == 0 and path[-1] == 8


def test_shortest_path_same_node_is_zero():
    graph = _grid_graph()
    assert graph.shortest_path(4, 4) == ([4], 0.0)


def test_oneway_edges_block_the_reverse_direction():
    node_xy = {0: (0.0, 0.0), 1: (100.0, 0.0), 2: (200.0, 0.0)}
    edges = [
        {"from": 0, "to": 1, "length_m": 100.0, "oneway": True},
        {"from": 1, "to": 2, "length_m": 100.0, "oneway": True},
    ]
    graph = RoadGraph(_make_payload(node_xy, edges))

    path, dist = graph.shortest_path(0, 2)
    assert dist == pytest.approx(200.0)

    path_back, dist_back = graph.shortest_path(2, 0)
    assert path_back is None
    assert dist_back == float("inf")


def test_unreachable_nodes_return_none_and_infinity():
    node_xy = {0: (0.0, 0.0), 1: (100.0, 0.0), 2: (5000.0, 5000.0), 3: (5100.0, 5000.0)}
    edges = [
        {"from": 0, "to": 1, "length_m": 100.0},
        {"from": 2, "to": 3, "length_m": 100.0},
    ]
    graph = RoadGraph(_make_payload(node_xy, edges))
    path, dist = graph.shortest_path(0, 2)
    assert path is None
    assert dist == float("inf")


def test_nearest_node_matches_brute_force_search():
    # Le KD-tree doit renvoyer exactement le même nœud qu'une recherche
    # naïve (distance à tous les nœuds) : c'est le comportement qu'il remplace.
    rng = np.random.default_rng(42)
    node_xy = {i: tuple(pt) for i, pt in enumerate(rng.uniform(-5000, 5000, size=(300, 2)))}
    graph = RoadGraph(_make_payload(node_xy, edges=[]))

    node_ids = list(node_xy.keys())
    node_array = np.array([node_xy[nid] for nid in node_ids])

    for query_point in rng.uniform(-5000, 5000, size=(50, 2)):
        diffs = node_array - query_point
        brute_idx = int(np.argmin(np.sum(diffs * diffs, axis=1)))
        brute_id = node_ids[brute_idx]
        brute_dist = float(np.linalg.norm(node_array[brute_idx] - query_point))

        got_id, got_dist = graph.nearest_node(query_point)
        assert got_id == brute_id
        assert got_dist == pytest.approx(brute_dist, abs=1e-6)


def test_path_to_points_returns_xy_in_order():
    graph = _grid_graph(spacing=100.0)
    path, _ = graph.shortest_path(0, 2)
    points = graph.path_to_points(path)
    assert points.shape == (len(path), 2)
    assert np.allclose(points[0], [0.0, 0.0])
    assert np.allclose(points[-1], [0.0, 200.0])
