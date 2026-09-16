"""Tests d'intégration du module planner (plan_from_payload de bout en bout)."""
import numpy as np
import pytest

from runtodraw import planner

# Filet de sécurité transitoire : compare à planner_adapter (l'ancien point
# d'entrée, qui appelle shape_route_experiments_v16) pendant la migration.
# À supprimer une fois app.py branché sur runtodraw.planner.
import planner_adapter as legacy_planner


def _grid_payload(n=12, spacing=80.0):
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


def test_plan_from_payload_raises_on_missing_graph_payload():
    with pytest.raises(ValueError, match="graph_payload manquant"):
        planner.plan_from_payload({"distance_km": 5.0, "drawing": {"shape": "square"}})


def test_plan_from_payload_raises_on_invalid_graph_payload():
    with pytest.raises(ValueError, match="invalide"):
        planner.plan_from_payload({"graph_payload": {"nodes": []}, "distance_km": 5.0, "drawing": {}})


def test_plan_from_payload_shape_mode_returns_four_routes():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }
    result = planner.plan_from_payload(payload)
    assert len(result["routes"]) == 4
    assert {r["id"] for r in result["routes"]} == {"route-1", "route-2", "route-3", "route-4"}


def test_plan_from_payload_text_mode_returns_split_plus_four_whole_word_routes():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "text", "text": "RUN"},
        "tolerance_ratio": 0.10,
    }
    result = planner.plan_from_payload(payload)
    assert len(result["routes"]) == 5
    assert result["routes"][0]["variant"] == "Lettres indépendantes"
    assert len(result["routes"][0]["letters"]) == 3


@pytest.mark.parametrize("drawing", [
    {"mode": "shape", "shape": "square"},
    {"mode": "shape", "shape": "circle"},
    {"mode": "text", "text": "RUN"},
])
def test_matches_legacy_planner_adapter(drawing):
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": drawing,
        "tolerance_ratio": 0.10,
    }
    got = planner.plan_from_payload(payload)
    expected = legacy_planner.plan_from_payload(payload)

    assert got["summary"] == expected["summary"]
    assert len(got["routes"]) == len(expected["routes"])
    for g, e in zip(got["routes"], expected["routes"]):
        assert g["id"] == e["id"]
        assert g["label"] == e["label"]
        assert g["variant"] == e["variant"]
        assert g["total_distance_m"] == pytest.approx(e["total_distance_m"])
        assert g["shape_error"] == pytest.approx(e["shape_error"])
