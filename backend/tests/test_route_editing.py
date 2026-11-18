"""Tests de l'édition manuelle d'un itinéraire (déplacer / insérer / supprimer un point d'ancrage)."""
import numpy as np
import pytest

from runtodraw import route_editing as ed
from runtodraw.planner import plan_from_graph
from runtodraw.road_graph import RoadGraph
from tests.test_road_graph import LAT0, LON0, random_road_graph


@pytest.fixture(scope="module")
def graph():
    return RoadGraph(random_road_graph(3, n_side=40, step=70.0, oneway_ratio=0.0))


def make_segment(graph, shape_nodes):
    """Segment d'essai : ancrages = nœuds donnés, reliés par plus courts chemins."""
    path, anchors = ed.connect(graph, shape_nodes)
    return {"node_path": path, "anchors": anchors}


@pytest.fixture(scope="module")
def segment(graph):
    nodes = [int(i) for i in np.linspace(100, 1400, 6)]
    return make_segment(graph, nodes)


def latlon_of(graph, idx):
    x, y = graph.node_array[idx]
    from runtodraw.geometry import xy_to_latlon_m
    return xy_to_latlon_m(float(x), float(y), graph.center_lat, graph.center_lon)


def assert_valid(graph, seg):
    path, anchors = seg["node_path"], seg["anchors"]
    # chaîne continue : chaque pas existe réellement dans le graphe
    for a, b in zip(path[:-1], path[1:]):
        _, cost = graph.shortest_path_idx(a, b)
        assert cost < float("inf")
    assert anchors == sorted(set(anchors))
    assert all(0 <= a < len(path) for a in anchors)


def test_move_changes_only_the_neighbour_legs(graph, segment):
    k = 2
    before = segment["node_path"]
    target = segment["node_path"][segment["anchors"][k]] + 1
    lat, lon = latlon_of(graph, target)
    out = ed.apply_operation(graph, segment, {"type": "move", "anchor": k, "lat": lat, "lon": lon})
    assert_valid(graph, out)
    assert len(out["anchors"]) == len(segment["anchors"])
    assert out["node_path"][out["anchors"][k]] == target
    # tout ce qui précède l'ancrage k-1 et suit l'ancrage k+1 est intact
    a_lo, a_hi = segment["anchors"][k - 1], segment["anchors"][k + 1]
    assert out["node_path"][:a_lo + 1] == before[:a_lo + 1]
    assert out["node_path"][out["anchors"][k + 1]:] == before[a_hi:]


def test_move_end_anchors(graph, segment):
    for k in (0, len(segment["anchors"]) - 1):
        target = segment["node_path"][segment["anchors"][k]] + 2
        lat, lon = latlon_of(graph, target)
        out = ed.apply_operation(graph, segment, {"type": "move", "anchor": k, "lat": lat, "lon": lon})
        assert_valid(graph, out)
        assert out["node_path"][out["anchors"][k]] == target


def test_insert_adds_one_anchor_between_neighbours(graph, segment):
    k = 1
    target = segment["node_path"][segment["anchors"][k]] + 40
    lat, lon = latlon_of(graph, target)
    out = ed.apply_operation(graph, segment, {"type": "insert", "anchor": k, "lat": lat, "lon": lon})
    assert_valid(graph, out)
    assert len(out["anchors"]) == len(segment["anchors"]) + 1
    assert out["node_path"][out["anchors"][k + 1]] == target


def test_delete_middle_first_and_last(graph, segment):
    n = len(segment["anchors"])
    for k in (0, 2, n - 1):
        out = ed.apply_operation(graph, segment, {"type": "delete", "anchor": k})
        assert_valid(graph, out)
        assert len(out["anchors"]) == n - 1
    # supprimer un point intermédiaire ne peut pas rallonger le tracé au-delà du détour déjà fait
    out = ed.apply_operation(graph, segment, {"type": "delete", "anchor": 2})
    assert ed.path_length_m(graph, out["node_path"]) <= ed.path_length_m(graph, segment["node_path"]) + 1e-6


def test_delete_refused_below_two_anchors(graph):
    seg = make_segment(graph, [100, 900])
    with pytest.raises(ed.EditError):
        ed.apply_operation(graph, seg, {"type": "delete", "anchor": 0})


def test_point_far_from_roads_is_refused(graph, segment):
    with pytest.raises(ed.EditError):
        ed.apply_operation(graph, segment, {"type": "move", "anchor": 1, "lat": LAT0 + 1.0, "lon": LON0})


def test_unreachable_target_is_refused(graph, segment):
    # l'îlot déconnecté du graphe de test (nœuds 1 à 3) n'est jamais atteint : on vise donc son voisinage
    island = [i for i, nid in enumerate(graph.node_ids) if nid in (1, 2, 3)]
    if not island:
        pytest.skip("îlot exclu du réseau principal : déjà inaccessible au snapping")
    lat, lon = latlon_of(graph, island[0])
    with pytest.raises(ed.EditError):
        ed.apply_operation(graph, segment, {"type": "move", "anchor": 1, "lat": lat, "lon": lon})


def test_unknown_anchor_and_operation(graph, segment):
    with pytest.raises(ed.EditError):
        ed.apply_operation(graph, segment, {"type": "delete", "anchor": 99})
    with pytest.raises(ed.EditError):
        ed.apply_operation(graph, segment, {"type": "teleport", "anchor": 0})


def test_linked_text_recomputes_adjacent_links(graph):
    res = plan_from_graph(graph, 3.0, {"mode": "text", "text": "LE"})
    linked = next(r for r in res["routes"] if r["kind"] == "letters_linked")
    segs = [{"kind": s["kind"], "node_path": [graph._idx_of[n] for n in s["node_path"]],
             "anchors": s["anchors"]} for s in linked["segments"]]
    letter = next(i for i, s in enumerate(segs) if s["kind"] == "letter" and i > 0)
    k = 0   # le premier point de la lettre touche la liaison qui la précède
    target = segs[letter]["node_path"][segs[letter]["anchors"][k]] + 1
    lat, lon = latlon_of(graph, target)
    out = ed.edit_route(graph, segs, letter, {"type": "move", "anchor": k, "lat": lat, "lon": lon})
    link = out[letter - 1]
    assert link["kind"] == "link"
    assert link["node_path"][0] == out[letter - 2]["node_path"][-1]
    assert link["node_path"][-1] == out[letter]["node_path"][0]
    with pytest.raises(ed.EditError):
        ed.edit_route(graph, segs, letter - 1, {"type": "delete", "anchor": 0})
