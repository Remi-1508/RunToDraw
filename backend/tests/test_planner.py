"""Propositions de formes : classement, recommandation et option « passer par le départ »."""
from runtodraw.planner import plan_from_graph, variant_text
from runtodraw.road_graph import RoadGraph
from tests.test_road_graph import random_road_graph

DRAWING = {"mode": "shape", "shape": "heart"}


def make_plan(**options):
    graph = RoadGraph(random_road_graph(5, n_side=45, step=70.0, oneway_ratio=0.0))
    return graph, plan_from_graph(graph, 6.0, DRAWING, **options)


def test_routes_are_sorted_best_first_and_the_first_is_recommended():
    _, plan = make_plan()
    scores = [route["score"] for route in plan["routes"]]
    assert scores == sorted(scores)
    assert plan["routes"][0].get("best") is True
    assert not any(route.get("best") for route in plan["routes"][1:])


def test_variant_text_is_plain_language():
    assert variant_text({"closest"}, 15000.0) == "Au plus près de tes 15 km"
    assert variant_text({"compromise"}, 15000.0) == "Meilleur compromis forme et distance"
    assert "·" in variant_text({"closest", "compromise"}, 6500.0)
    assert not any(word in variant_text({"closest", "compromise"}, 6500.0) for word in ("Projection", "Translation"))


def test_through_start_keeps_only_routes_that_start_and_return_to_the_start_point():
    graph, plan = make_plan(through_start=True)
    assert plan["routes"] and all(route["includes_start"] for route in plan["routes"])
    start_id = graph.node_ids[int(graph.nearest_indices([[0.0, 0.0]])[0][0])]
    for route in plan["routes"]:
        path = route["segments"][0]["node_path"]
        assert path[0] == start_id and path[-1] == start_id   # forme fermée : départ = arrivée

