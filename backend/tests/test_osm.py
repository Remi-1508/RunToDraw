"""Tests unitaires du module osm (requête Overpass, conversion en graphe)."""
import pytest

from runtodraw import osm

# Filet de sécurité transitoire : compare à la fonction équivalente de app.py
# pendant la migration. À supprimer une fois app.py branché sur runtodraw.osm.
from app import build_graph_from_overpass as legacy_build_graph_from_overpass


SAMPLE_OSM_JSON = {
    "elements": [
        {"type": "node", "id": 1, "lat": 44.840, "lon": -0.580},
        {"type": "node", "id": 2, "lat": 44.841, "lon": -0.580},
        {"type": "node", "id": 3, "lat": 44.842, "lon": -0.580},
        {"type": "way", "id": 100, "nodes": [1, 2, 3], "tags": {"highway": "residential"}},
        {"type": "way", "id": 101, "nodes": [2, 1], "tags": {"highway": "residential", "oneway": "yes"}},
        {"type": "way", "id": 102, "nodes": [999]},  # way trop courte, ignorée
    ],
}


def test_build_overpass_query_circle_embeds_coordinates_and_radius():
    query = osm.build_overpass_query_circle(44.84, -0.58, 7500.3)
    assert "around:7500,44.84,-0.58" in query
    assert "motorway" in query  # bien exclue de la requête
    assert "[out:json]" in query


def test_build_graph_from_overpass_creates_nodes_and_bidirectional_edges():
    graph = osm.build_graph_from_overpass(SAMPLE_OSM_JSON)
    assert {n["id"] for n in graph["nodes"]} == {1, 2, 3}

    edge_pairs = {(e["from"], e["to"], e["oneway"]) for e in graph["edges"]}
    assert (1, 2, False) in edge_pairs
    assert (2, 3, False) in edge_pairs
    assert (2, 1, True) in edge_pairs  # sens unique explicite, non dupliqué en (1, 2)


def test_build_graph_from_overpass_matches_legacy_app_py():
    got = osm.build_graph_from_overpass(SAMPLE_OSM_JSON)
    expected = legacy_build_graph_from_overpass(SAMPLE_OSM_JSON)
    assert got["nodes"] == expected["nodes"]
    assert len(got["edges"]) == len(expected["edges"])
    for a, b in zip(got["edges"], expected["edges"]):
        assert a["from"] == b["from"] and a["to"] == b["to"] and a["oneway"] == b["oneway"]
        assert a["length_m"] == pytest.approx(b["length_m"])


def test_fetch_overpass_with_fallback_tries_next_endpoint_on_failure(monkeypatch):
    calls = []

    def fake_post_overpass(endpoint, query):
        calls.append(endpoint)
        if len(calls) < 2:
            raise RuntimeError("boom")
        return {"elements": []}

    monkeypatch.setattr(osm, "post_overpass", fake_post_overpass)
    monkeypatch.setattr(osm.time, "sleep", lambda s: None)

    result = osm.fetch_overpass_with_fallback("fake query")
    assert result == {"elements": []}
    assert calls == osm.OVERPASS_ENDPOINTS[:2]


def test_fetch_overpass_with_fallback_raises_last_error_after_max_tries(monkeypatch):
    def always_fails(endpoint, query):
        raise RuntimeError(f"down: {endpoint}")

    monkeypatch.setattr(osm, "post_overpass", always_fails)
    monkeypatch.setattr(osm.time, "sleep", lambda s: None)

    with pytest.raises(RuntimeError, match="down:"):
        osm.fetch_overpass_with_fallback("fake query", max_tries=2)


def test_fetch_road_graph_builds_meta_and_uses_half_distance_as_radius(monkeypatch):
    monkeypatch.setattr(osm, "fetch_overpass_with_fallback", lambda query: SAMPLE_OSM_JSON)

    payload = osm.fetch_road_graph(lat=44.84, lon=-0.58, distance_km=10.0)

    assert payload["meta"]["center"] == [44.84, -0.58]
    assert payload["meta"]["radius_km"] == pytest.approx(5.0)
    assert len(payload["nodes"]) == 3
