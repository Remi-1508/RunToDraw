"""Test du cache de graphes : plusieurs demandes simultanées pour une même zone ne téléchargent qu'une fois."""
import threading
import time

import pytest

from runtodraw import graph_cache


class FakeGraph:
    def __init__(self, payload):
        self.node_ids = [1, 2, 3]
        self.nodes = self.edges = True


@pytest.fixture
def fake_network(monkeypatch):
    calls = {"downloads": 0}

    def fake_fetch(query):
        calls["downloads"] += 1
        time.sleep(0.1)  # laisse aux autres threads le temps d'arriver
        return {}

    monkeypatch.setattr(graph_cache, "fetch_overpass_with_fallback", fake_fetch)
    monkeypatch.setattr(graph_cache, "build_graph_from_overpass", lambda osm: {"nodes": [1, 2, 3], "edges": [1, 2]})
    monkeypatch.setattr(graph_cache, "RoadGraph", FakeGraph)
    graph_cache._graph_cache.clear()
    graph_cache._download_locks.clear()
    yield calls
    graph_cache._graph_cache.clear()
    graph_cache._download_locks.clear()


def test_concurrent_requests_for_same_zone_download_once(fake_network):
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(graph_cache.get_road_graph(44.84, -0.58, 5000)))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert fake_network["downloads"] == 1
    assert len(results) == 5 and all(r is results[0] for r in results)


def test_second_call_uses_cache(fake_network):
    graph_cache.get_road_graph(44.84, -0.58, 5000)
    graph_cache.get_road_graph(44.84, -0.58, 5000)
    assert fake_network["downloads"] == 1


def test_empty_area_raises_no_roads(monkeypatch):
    monkeypatch.setattr(graph_cache, "fetch_overpass_with_fallback", lambda q: {})
    monkeypatch.setattr(graph_cache, "build_graph_from_overpass", lambda osm: {"nodes": [], "edges": []})
    graph_cache._graph_cache.clear()
    with pytest.raises(graph_cache.NoRoadsFoundError):
        graph_cache.get_road_graph(0.0, 0.0, 1000)
