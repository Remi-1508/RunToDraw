"""Réseaux routiers préchargés : choix de la ville, extraction de la zone, intégration au cache de graphes."""
import pytest

from runtodraw import graph_cache, prebuilt
from runtodraw.road_graph import RoadGraph

CENTER = (44.84, -0.58)


def grid_graph(n=20, step=0.001):
    """Quadrillage de rues autour de CENTER : n x n nœuds espacés de `step` degrés (~100 m)."""
    nodes = [{"id": i * n + j + 1, "lat": CENTER[0] + (i - n // 2) * step, "lon": CENTER[1] + (j - n // 2) * step}
             for i in range(n) for j in range(n)]
    edges = []
    for i in range(n):
        for j in range(n):
            a = i * n + j + 1
            if j + 1 < n:
                edges.append({"from": a, "to": a + 1, "length_m": 80.0, "oneway": False})
            if i + 1 < n:
                edges.append({"from": a, "to": a + n, "length_m": 111.0, "oneway": (i + j) % 7 == 0})
    return {"nodes": nodes, "edges": edges}


@pytest.fixture
def data_dir(tmp_path):
    prebuilt._loaded.clear()
    prebuilt.save_city("test", CENTER[0], CENTER[1], 1500, grid_graph(), data_dir=tmp_path)
    yield tmp_path
    prebuilt._loaded.clear()


def test_zone_inside_a_city_is_found_and_outside_is_not(data_dir):
    assert prebuilt.find_city(*CENTER, 1000, data_dir)["name"] == "test"
    assert prebuilt.find_city(CENTER[0] + 0.005, CENTER[1], 800, data_dir) is not None   # ~550 m + 800 m < 1500 m
    assert prebuilt.find_city(*CENTER, 1800, data_dir) is None                           # rayon trop grand
    assert prebuilt.find_city(CENTER[0] + 0.1, CENTER[1], 500, data_dir) is None         # trop loin de la ville
    assert prebuilt.find_city(*CENTER, 500, data_dir / "inexistant") is None


def test_crop_keeps_only_the_requested_box_with_consistent_edges(data_dir):
    city = prebuilt.find_city(*CENTER, 400, data_dir)
    raw = prebuilt.crop_city_graph(city, *CENTER, 400, data_dir)
    ids = {n["id"] for n in raw["nodes"]}
    assert 0 < len(ids) < 400
    assert all(e["from"] in ids and e["to"] in ids for e in raw["edges"])
    assert all(abs(n["lat"] - CENTER[0]) <= 400 / 111320.0 + 1e-9 for n in raw["nodes"])
    assert any(e["oneway"] for e in raw["edges"]) and any(not e["oneway"] for e in raw["edges"])
    assert all(e["length_m"] > 0 for e in raw["edges"])
    # le graphe obtenu est directement utilisable par le moteur
    graph = RoadGraph({"meta": {"center": list(CENTER), "radius_km": 0.4}, **raw})
    assert len(graph.node_ids) == len(ids)


def test_graph_cache_uses_prebuilt_before_overpass(data_dir, monkeypatch):
    monkeypatch.setattr(prebuilt, "DATA_DIR", data_dir)
    monkeypatch.setattr(graph_cache, "fetch_overpass_with_fallback",
                        lambda query: pytest.fail("Overpass ne doit pas être appelé pour une ville préchargée"))
    graph_cache._graph_cache.clear()
    graph = graph_cache.get_road_graph(*CENTER, 400)
    assert len(graph.node_ids) > 10
    graph_cache._graph_cache.clear()


def test_loaded_cities_are_bounded_in_memory(tmp_path, monkeypatch):
    """Beaucoup de villes préchargées ne doivent pas faire grossir la mémoire : seules les dernières restent chargées."""
    prebuilt._loaded.clear()
    monkeypatch.setattr(prebuilt, "MAX_LOADED", 2)
    for i in range(4):
        prebuilt.save_city(f"ville{i}", CENTER[0] + i, CENTER[1], 1500, grid_graph(5), data_dir=tmp_path)
    for city in prebuilt._read_index(tmp_path):
        prebuilt._load_arrays(city, tmp_path)
    assert len(prebuilt._loaded) == 2
    prebuilt._loaded.clear()
