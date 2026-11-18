"""Tests de l'API (nécessitent fastapi et httpx : pip install -r requirements-dev.txt)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from runtodraw import api  # noqa: E402

client = TestClient(api.app)
BODY = {"lat": 44.84, "lon": -0.58, "distance_km": 10, "drawing": {"mode": "shape", "shape": "heart"}}


@pytest.fixture(autouse=True)
def no_rate_limit(monkeypatch):
    monkeypatch.setattr(api.rate_limiter, "limit", 10_000)


@pytest.fixture
def fake_graph(monkeypatch):
    class G:
        node_ids = [1, 2]
        segment_count = 1

    monkeypatch.setattr(api, "get_road_graph", lambda lat, lon, radius: G())
    monkeypatch.setattr(api, "plan_from_graph", lambda *a, **k: {"summary": "ok", "routes": []})


def test_health_exposes_server_limits():
    assert client.get("/health").json() == {"ok": True, "max_distance_km": api.settings.max_distance_km}


def test_fetch_and_plan_accept_valid_request(fake_graph):
    assert client.post("/api/graph/fetch", json=BODY).status_code == 200
    assert client.post("/api/routes/plan", json=BODY).json()["summary"] == "ok"


@pytest.mark.parametrize("patch", [
    {"distance_km": 5000},
    {"distance_km": 0},
    {"lat": 123},
    {"drawing": {"mode": "shape", "shape": "dragon"}},
    {"drawing": {"mode": "text", "text": "!!!"}},
    {"drawing": {"mode": "text", "text": "ABCDEFGHIJKL"}},
])
def test_invalid_requests_are_rejected(fake_graph, patch):
    assert client.post("/api/routes/plan", json={**BODY, **patch}).status_code == 422


def test_text_with_accents_is_accepted(fake_graph):
    body = {**BODY, "drawing": {"mode": "text", "text": "Été"}}
    assert client.post("/api/routes/plan", json=body).status_code == 200


def test_legacy_graph_payload_is_ignored_not_executed(fake_graph):
    assert client.post("/api/routes/plan", json={**BODY, "graph_payload": {"nodes": []}}).status_code == 200


def test_rate_limit_returns_429(fake_graph, monkeypatch):
    monkeypatch.setattr(api.rate_limiter, "limit", 1)
    api.rate_limiter._hits.clear()
    assert client.post("/api/routes/plan", json=BODY).status_code == 200
    resp = client.post("/api/routes/plan", json=BODY)
    assert resp.status_code == 429 and "Retry-After" in resp.headers


def test_cors_allows_configured_origin_only(fake_graph):
    ok = client.options("/api/routes/plan", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    bad = client.options("/api/routes/plan", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
