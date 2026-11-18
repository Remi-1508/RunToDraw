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


# ---------- Édition manuelle (POST /api/routes/edit) ----------

@pytest.fixture
def edit_graph(monkeypatch):
    """Vrai petit graphe routier (grille synthétique) à la place du téléchargement Overpass."""
    from runtodraw.road_graph import RoadGraph
    from tests.test_road_graph import random_road_graph

    graph = RoadGraph(random_road_graph(3, n_side=40, step=70.0, oneway_ratio=0.0))
    monkeypatch.setattr(api, "get_road_graph", lambda lat, lon, radius: graph)
    api.edit_rate_limiter._hits.clear()
    monkeypatch.setattr(api.edit_rate_limiter, "limit", 10_000)
    return graph


def _edit_body(graph, **override):
    from runtodraw import route_editing as ed
    path, anchors = ed.connect(graph, [100, 500, 900, 1300])
    body = {
        **BODY,
        "segments": [{"label": "Cœur", "kind": "shape", "anchors": anchors,
                      "node_path": [graph.node_ids[i] for i in path]}],
        "segment_index": 0,
        "operation": {"type": "delete", "anchor": 1},
    }
    body.update(override)
    return body


def test_edit_delete_returns_recomputed_segment(edit_graph):
    resp = client.post("/api/routes/edit", json=_edit_body(edit_graph))
    assert resp.status_code == 200
    data = resp.json()
    seg = data["segments"][0]
    assert len(seg["anchors"]) == 3 and len(seg["points"]) == len(seg["node_path"])
    assert data["total_distance_m"] == pytest.approx(seg["distance_m"])


def test_edit_move_snaps_to_the_dropped_position(edit_graph):
    from runtodraw.geometry import xy_to_latlon_m
    x, y = edit_graph.node_array[600]
    lat, lon = xy_to_latlon_m(float(x), float(y), edit_graph.center_lat, edit_graph.center_lon)
    body = _edit_body(edit_graph, operation={"type": "move", "anchor": 1, "lat": lat, "lon": lon})
    seg = client.post("/api/routes/edit", json=body).json()["segments"][0]
    assert seg["node_path"][seg["anchors"][1]] == edit_graph.node_ids[600]


@pytest.mark.parametrize("patch", [
    {"operation": {"type": "move", "anchor": 1}},                       # position manquante
    {"operation": {"type": "explode", "anchor": 1}},                    # opération inconnue
    {"segments": []},
    {"segment_index": 5},
])
def test_edit_invalid_requests_are_rejected(edit_graph, patch):
    assert client.post("/api/routes/edit", json=_edit_body(edit_graph, **patch)).status_code == 422


def test_edit_rejects_inconsistent_anchors(edit_graph):
    body = _edit_body(edit_graph)
    body["segments"][0]["anchors"] = [0, 99999]
    assert client.post("/api/routes/edit", json=body).status_code == 422


def test_edit_rejects_nodes_unknown_to_the_loaded_map(edit_graph):
    body = _edit_body(edit_graph)
    body["segments"][0]["node_path"][2] = -42
    assert client.post("/api/routes/edit", json=body).status_code == 422


def test_edit_far_from_roads_gives_a_clear_error(edit_graph):
    body = _edit_body(edit_graph, operation={"type": "move", "anchor": 1, "lat": 10.0, "lon": 10.0})
    resp = client.post("/api/routes/edit", json=body)
    assert resp.status_code == 422 and "éloigné" in resp.json()["detail"]


def test_edit_has_its_own_rate_limit(edit_graph, monkeypatch):
    monkeypatch.setattr(api.edit_rate_limiter, "limit", 1)
    api.edit_rate_limiter._hits.clear()
    assert client.post("/api/routes/edit", json=_edit_body(edit_graph)).status_code == 200
    assert client.post("/api/routes/edit", json=_edit_body(edit_graph)).status_code == 429


SQUARE_POINTS = [[0, 0], [100, 0], [100, 100], [0, 100], [2, 3]]


def test_custom_drawing_is_accepted_and_cleaned(fake_graph):
    body = {**BODY, "drawing": {"mode": "custom", "points": SQUARE_POINTS}}
    assert client.post("/api/routes/plan", json=body).status_code == 200
    drawing = api.GraphFetchRequest(**body).drawing
    assert drawing.points[0] == drawing.points[-1]        # presque refermé : le serveur ferme la forme


@pytest.mark.parametrize("drawing", [
    {"mode": "custom"},                                              # pas de points
    {"mode": "custom", "points": []},
    {"mode": "custom", "points": [[1, 2]]},                         # un seul point
    {"mode": "custom", "points": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},  # mauvaise forme
    {"mode": "custom", "points": [[0, i] for i in range(2001)]},     # trop de points
    {"mode": "custom", "points": [[0, 0], [1e12, 5], [3, 4]]},      # coordonnées absurdes
])
def test_invalid_custom_drawings_are_rejected(fake_graph, drawing):
    assert client.post("/api/routes/plan", json={**BODY, "drawing": drawing}).status_code == 422


def test_points_are_ignored_outside_custom_mode(fake_graph):
    body = {**BODY, "drawing": {"mode": "shape", "shape": "heart", "points": [[1, 2]]}}
    assert api.GraphFetchRequest(**body).drawing.points is None
    assert client.post("/api/routes/plan", json=body).status_code == 200
