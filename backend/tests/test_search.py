"""Tests unitaires du module search (candidats, evaluate_method, texte séparé)."""
import numpy as np
import pytest

from runtodraw import search, shapes
from runtodraw.graph import RoadGraph

# Filet de sécurité transitoire : compare aux fonctions équivalentes de la V16
# pendant la migration. À supprimer quand shape_route_experiments_v16 sera
# retiré du dépôt.
import shape_route_experiments_v16 as legacy


def _grid_payload(n=12, spacing=80.0):
    """Grille n x n assez dense pour que la recherche de forme trouve un vrai chemin."""
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


@pytest.fixture(scope="module")
def grid_graph():
    return RoadGraph(_grid_payload())


def test_graph_center_is_the_middle_of_the_bounds(grid_graph):
    center = search.graph_center(grid_graph)
    assert center[0] == pytest.approx(0.5 * (grid_graph.bounds["xmin"] + grid_graph.bounds["xmax"]))
    assert center[1] == pytest.approx(0.5 * (grid_graph.bounds["ymin"] + grid_graph.bounds["ymax"]))


def test_make_candidate_points_scales_rotates_and_translates():
    base = shapes.make_square()
    target = search.make_candidate_points(base, center=np.array([100.0, 200.0]), size_m=40.0, angle_deg=0.0)
    extent = target.max(axis=0) - target.min(axis=0)
    assert extent.max() == pytest.approx(40.0)
    bbox_center = (target.min(axis=0) + target.max(axis=0)) / 2
    assert np.allclose(bbox_center, [100.0, 200.0], atol=1e-6)


def test_global_search_candidates_translation_has_more_centers_than_projection(grid_graph):
    base = shapes.make_circle()
    projection = search.global_search_candidates(grid_graph, base, 1000.0, "circle", use_translation=False)
    translation = search.global_search_candidates(grid_graph, base, 1000.0, "circle", use_translation=True)
    assert len(translation) == 5 * len(projection)


def test_evaluate_method_returns_a_feasible_or_best_effort_candidate(grid_graph):
    base = shapes.make_square()
    result = search.evaluate_method(grid_graph, base, desired_distance_m=800.0, tolerance_ratio=0.10,
                                     shape_name="square", method_name="projection")
    assert "closest_to_distance" in result and "best_compromise" in result
    assert result["all_candidates_count"] > 0
    assert result["closest_to_distance"]["metrics"]["length_route"] >= 0.0


def test_split_text_each_letter_gets_the_full_requested_distance(grid_graph):
    # Comportement voulu (pas un bug) : en mode "lettres indépendantes", chaque
    # lettre est cherchée avec la distance complète demandée par l'utilisateur,
    # pas une fraction. C'est ce qui permet de comparer "un mot compressé dans
    # la distance" à "chaque lettre pleinement développée sur cette distance".
    results = search.split_text_itineraries_full_distance(grid_graph, "RUN", per_letter_distance_m=800.0, tolerance_ratio=0.10)
    assert [r["letter"] for r in results] == ["R", "U", "N"]
    for r in results:
        assert r["target_distance"] == 800.0


@pytest.mark.parametrize("shape_name", ["square", "circle"])
def test_evaluate_method_matches_legacy_v16(grid_graph, shape_name):
    base = shapes.get_base_shape(shape_name, text="P2I")
    got = search.evaluate_method(grid_graph, base, 800.0, 0.10, shape_name, "projection")

    legacy_graph = legacy.RoadGraph(_grid_payload())
    legacy_base = legacy.get_base_shape(shape_name, "P2I")
    expected = legacy.evaluate_method(legacy_graph, legacy_base, 800.0, 0.10, shape_name, "projection")

    assert got["all_candidates_count"] == expected["all_candidates_count"]
    for key in ["closest_to_distance", "best_compromise"]:
        assert got[key]["metrics"]["length_route"] == pytest.approx(expected[key]["metrics"]["length_route"])
        assert got[key]["metrics"]["combined"] == pytest.approx(expected[key]["metrics"]["combined"])


@pytest.mark.parametrize("text", ["RUN", "I1MW"])
def test_split_text_matches_legacy_v16(grid_graph, text):
    # "I1MW" exerce spécifiquement les tailles élargies pour "I"/"1" et la
    # branche (redondante) "M"/"W" de la V16 : on vérifie qu'elles donnent
    # toujours des résultats identiques après simplification.
    got = search.split_text_itineraries_full_distance(grid_graph, text, 800.0, 0.10)

    legacy_graph = legacy.RoadGraph(_grid_payload())
    expected = legacy.split_text_itineraries_full_distance(legacy_graph, text, 800.0, 0.10)

    assert [r["letter"] for r in got] == [r["letter"] for r in expected]
    for g, e in zip(got, expected):
        assert g["metrics"]["length_route"] == pytest.approx(e["metrics"]["length_route"])
        assert g["metrics"]["size_m"] == pytest.approx(e["metrics"]["size_m"])
