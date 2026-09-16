"""Test d'intégration de l'API FastAPI elle-même (app.py branché sur runtodraw)."""
import time

import numpy as np
from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


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


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_graph_fetch_delegates_to_runtodraw_osm(monkeypatch):
    called = {}

    def fake_fetch_road_graph(lat, lon, distance_km):
        called["args"] = (lat, lon, distance_km)
        return {"meta": {"center": [lat, lon], "radius_km": distance_km / 2}, "nodes": [], "edges": []}

    monkeypatch.setattr(app_module, "fetch_road_graph", fake_fetch_road_graph)

    res = client.post("/api/graph/fetch", json={"lat": 44.84, "lon": -0.58, "distance_km": 10.0})
    assert res.status_code == 200
    assert called["args"] == (44.84, -0.58, 10.0)
    assert res.json()["meta"]["radius_km"] == 5.0


def test_routes_plan_end_to_end_through_the_real_http_api():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }
    res = client.post("/api/routes/plan", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert len(body["routes"]) == 4
    assert body["routes"][0]["segments"][0]["points"]  # des points GPS ont bien été renvoyés


def test_routes_plan_jobs_end_to_end_with_real_polling():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }

    res = client.post("/api/routes/plan/jobs", json=payload)
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    seen_progress = []
    deadline = time.time() + 15.0
    body = None
    while time.time() < deadline:
        res = client.get(f"/api/routes/plan/jobs/{job_id}")
        assert res.status_code == 200
        body = res.json()
        seen_progress.append(body["progress"])
        if body["status"] == "done":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("le job n'a pas terminé à temps")

    assert body["status"] == "done"
    assert body["progress"] == 1.0
    assert seen_progress == sorted(seen_progress)
    assert len(body["result"]["routes"]) == 4


def test_routes_plan_jobs_unknown_id_returns_404():
    res = client.get("/api/routes/plan/jobs/does-not-exist")
    assert res.status_code == 404


def test_routes_plan_jobs_reports_error_status_for_invalid_payload():
    res = client.post("/api/routes/plan/jobs", json={
        "graph_payload": {"nodes": [], "edges": []},
        "distance_km": 5.0,
        "drawing": {},
    })
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    deadline = time.time() + 10.0
    body = None
    while time.time() < deadline:
        body = client.get(f"/api/routes/plan/jobs/{job_id}").json()
        if body["status"] == "error":
            break
        time.sleep(0.02)
    else:
        raise AssertionError("le job n'a pas termine a temps")

    assert body["status"] == "error"
    assert "invalide" in body["error"]
