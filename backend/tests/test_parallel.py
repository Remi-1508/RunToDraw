"""Tests de la parallélisation (parallel.py + support executor de search.py)."""
import numpy as np
import pytest

from runtodraw import parallel, planner, search, shapes
from runtodraw.graph import RoadGraph


def _grid_payload(n=20, spacing=60.0):
    node_xy = {i * n + j: (i * spacing, j * spacing) for i in range(n) for j in range(n)}
    nodes = []
    for nid, (x, y) in node_xy.items():
        lon = np.degrees(x / 6_371_000.0)
        lat = np.degrees(y / 6_371_000.0)
        nodes.append({"id": nid, "lat": lat, "lon": lon})

    edges = []
    for i in range(n):
        for j in range(n):
            nid = i * n + j
            if i + 1 < n:
                edges.append({"from": nid, "to": (i + 1) * n + j, "length_m": spacing})
            if j + 1 < n:
                edges.append({"from": nid, "to": i * n + (j + 1), "length_m": spacing})
    return {"meta": {"center": [0.0, 0.0]}, "nodes": nodes, "edges": edges}


def test_evaluate_method_parallel_matches_sequential():
    graph = RoadGraph(_grid_payload())
    base = shapes.make_square()

    sequential = search.evaluate_method(graph, base, 800.0, 0.10, "square", "translation", executor=None)
    with parallel.make_executor(max_workers=2) as executor:
        parallel_result = search.evaluate_method(graph, base, 800.0, 0.10, "square", "translation", executor=executor)

    assert parallel_result["all_candidates_count"] == sequential["all_candidates_count"]
    for key in ["closest_to_distance", "best_compromise"]:
        assert parallel_result[key]["metrics"]["length_route"] == pytest.approx(
            sequential[key]["metrics"]["length_route"]
        )
        assert parallel_result[key]["metrics"]["combined"] == pytest.approx(sequential[key]["metrics"]["combined"])


def test_split_text_parallel_matches_sequential():
    graph = RoadGraph(_grid_payload())

    sequential = search.split_text_itineraries_full_distance(graph, "RUN", 800.0, 0.10, executor=None)
    with parallel.make_executor(max_workers=2) as executor:
        parallel_result = search.split_text_itineraries_full_distance(graph, "RUN", 800.0, 0.10, executor=executor)

    assert [r["letter"] for r in parallel_result] == [r["letter"] for r in sequential]
    for p, s in zip(parallel_result, sequential):
        assert p["metrics"]["length_route"] == pytest.approx(s["metrics"]["length_route"])
        assert p["metrics"]["size_m"] == pytest.approx(s["metrics"]["size_m"])


def test_plan_from_payload_uses_the_thread_pool(monkeypatch):
    created = {}
    real_make_executor = parallel.make_executor

    def spying_make_executor(max_workers=None):
        created["called"] = True
        return real_make_executor(max_workers=max_workers)

    monkeypatch.setattr(planner.parallel, "make_executor", spying_make_executor)

    result = planner.plan_from_payload({
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    })

    assert created.get("called") is True
    assert len(result["routes"]) == 4
