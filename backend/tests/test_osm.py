"""Tests de la récupération Overpass avec requêtes de secours échelonnées."""
import time

import pytest

from runtodraw import osm


def fake_post(behaviours):
    """behaviours : {endpoint: (délai en s, résultat ou exception)}."""
    def post(endpoint, query):
        delay, outcome = behaviours[endpoint]
        time.sleep(delay)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    return post


def test_slow_first_server_does_not_delay_the_answer(monkeypatch):
    monkeypatch.setattr(osm, "post_overpass", fake_post({"a": (3.0, {"from": "a"}), "b": (0.05, {"from": "b"})}))
    t0 = time.perf_counter()
    result = osm.fetch_overpass_with_fallback("q", endpoints=["a", "b"], hedge_delay_s=0.1)
    assert result == {"from": "b"}
    assert time.perf_counter() - t0 < 1.0


def test_failing_server_falls_through_immediately(monkeypatch):
    monkeypatch.setattr(osm, "post_overpass", fake_post({"a": (0.0, RuntimeError("504")), "b": (0.0, {"ok": 1})}))
    t0 = time.perf_counter()
    assert osm.fetch_overpass_with_fallback("q", endpoints=["a", "b"], hedge_delay_s=30.0) == {"ok": 1}
    assert time.perf_counter() - t0 < 1.0   # pas besoin d'attendre le délai de 30 s


def test_first_server_wins_when_fast(monkeypatch):
    monkeypatch.setattr(osm, "post_overpass", fake_post({"a": (0.0, {"from": "a"}), "b": (0.0, {"from": "b"})}))
    assert osm.fetch_overpass_with_fallback("q", endpoints=["a", "b"], hedge_delay_s=5.0) == {"from": "a"}


def test_all_servers_failing_raises_the_last_error(monkeypatch):
    monkeypatch.setattr(osm, "post_overpass", fake_post({"a": (0.0, RuntimeError("x")), "b": (0.0, RuntimeError("y"))}))
    with pytest.raises(RuntimeError):
        osm.fetch_overpass_with_fallback("q", endpoints=["a", "b"], hedge_delay_s=0.1)


def test_query_keeps_foot_oneway_tags_only_and_builds_a_graph():
    query = osm.build_overpass_query_bbox(44.84, -0.58, 2000)
    assert "[bbox:" in query and "oneway:foot" in query and "parking_aisle" in query
    assert "sidewalk" not in query  # les trottoirs dessinés à part restent dans le réseau
    # Réponse au format produit par la requête : voie à sens unique piéton avec tags, autre voie « nue ».
    answer = {"elements": [
        {"type": "way", "id": 1, "nodes": [10, 11], "tags": {"oneway:foot": "yes"}},
        {"type": "way", "id": 2, "nodes": [11, 12]},
        {"type": "node", "id": 10, "lat": 44.0, "lon": -0.5},
        {"type": "node", "id": 11, "lat": 44.001, "lon": -0.5},
        {"type": "node", "id": 12, "lat": 44.002, "lon": -0.5},
    ]}
    graph = osm.build_graph_from_overpass(answer)
    assert [(e["from"], e["to"], e["oneway"]) for e in graph["edges"]] == [(10, 11, True), (11, 12, False)]
