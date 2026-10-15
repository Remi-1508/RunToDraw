"""Tests de RoadGraph : les optimisations (KD-tree, A*, accessibilité) doivent donner
exactement les mêmes réponses que les versions simples (force brute, Dijkstra)."""
import heapq
import math
import random

import numpy as np
import pytest

from shape_route_experiments_v16 import RoadGraph, route_from_target, get_base_shape, make_candidate_points

LAT0, LON0 = 44.8378, -0.5792


def haversine(a, b):
    la1, lo1 = map(math.radians, a)
    la2, lo2 = map(math.radians, b)
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def random_road_graph(seed, n_side=25, step=80.0, oneway_ratio=0.2, drop_ratio=0.15):
    """Grille bruitée avec sens uniques, arêtes supprimées et un îlot déconnecté."""
    rng = random.Random(seed)
    nodes, edges = {}, []

    def add_node(nid, x, y):
        nodes[nid] = (LAT0 + math.degrees(y / 6371000),
                      LON0 + math.degrees(x / (6371000 * math.cos(math.radians(LAT0)))))

    for i in range(n_side):
        for j in range(n_side):
            add_node(10_000 + i * n_side + j,
                     (i - n_side / 2) * step + rng.uniform(-20, 20),
                     (j - n_side / 2) * step + rng.uniform(-20, 20))
    for i in range(n_side):
        for j in range(n_side):
            u = 10_000 + i * n_side + j
            for v in ([u + n_side] if i + 1 < n_side else []) + ([u + 1] if j + 1 < n_side else []):
                if rng.random() < drop_ratio:
                    continue
                edges.append({"from": u, "to": v, "length_m": haversine(nodes[u], nodes[v]),
                              "oneway": rng.random() < oneway_ratio})
    # Îlot déconnecté : injoignable depuis le reste du graphe.
    for k, (x, y) in enumerate([(5000, 5000), (5060, 5000), (5060, 5060)]):
        add_node(1 + k, x, y)
    edges += [{"from": 1, "to": 2, "length_m": 60.0, "oneway": False},
              {"from": 2, "to": 3, "length_m": 60.0, "oneway": False}]
    return {"meta": {"center": [LAT0, LON0]},
            "nodes": [{"id": k, "lat": la, "lon": lo} for k, (la, lo) in nodes.items()],
            "edges": edges}


def reference_dijkstra(payload, start, goal):
    """Dijkstra « naïf » identique à l'ancienne version du moteur (référence)."""
    adj = {}
    for e in payload["edges"]:
        adj.setdefault(e["from"], []).append((e["to"], e["length_m"]))
        if not e["oneway"]:
            adj.setdefault(e["to"], []).append((e["from"], e["length_m"]))
    dist, pq = {start: 0.0}, [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist[u]:
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return math.inf


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_astar_matches_dijkstra(seed):
    payload = random_road_graph(seed)
    graph = RoadGraph(payload)
    rng = random.Random(100 + seed)
    ids = [n["id"] for n in payload["nodes"]]
    for _ in range(150):
        s, g = rng.choice(ids), rng.choice(ids)
        path, cost = graph.shortest_path(s, g)
        expected = reference_dijkstra(payload, s, g)
        if math.isinf(expected):
            assert path is None and math.isinf(cost)
            continue
        assert cost == pytest.approx(expected, rel=1e-12, abs=1e-9)
        assert path[0] == s and path[-1] == g
        # Le chemin renvoyé est valide et son coût correspond bien à la somme de ses arêtes.
        lengths = {}
        for e in payload["edges"]:
            lengths[(e["from"], e["to"])] = e["length_m"]
            if not e["oneway"]:
                lengths[(e["to"], e["from"])] = e["length_m"]
        assert sum(lengths[(a, b)] for a, b in zip(path, path[1:])) == pytest.approx(cost)


def test_disconnected_island_is_unreachable():
    graph = RoadGraph(random_road_graph(0))
    path, cost = graph.shortest_path(10_000, 1)
    assert path is None and math.isinf(cost)
    path, cost = graph.shortest_path(1, 3)
    assert path == [1, 2, 3] and cost == pytest.approx(120.0)


def test_nearest_node_matches_brute_force_on_main_network():
    """L'accroche ne vise que la plus grande composante fortement connexe (réseau principal)."""
    graph = RoadGraph(random_road_graph(3))
    main = graph._snap_idx
    assert 0 < len(main) < len(graph.node_ids)  # l'îlot et les nœuds isolés sont exclus
    rng = np.random.default_rng(0)
    for p in rng.uniform(-1200, 1200, size=(200, 2)):
        d2 = np.sum((graph.node_array[main] - p) ** 2, axis=1)
        nid, d = graph.nearest_node(p)
        assert d == pytest.approx(math.sqrt(d2.min()))
        assert graph.node_ids[int(main[np.argmin(d2)])] == nid


def test_snapping_never_lands_on_the_island():
    graph = RoadGraph(random_road_graph(0))
    island = [graph._idx_of[i] for i in (1, 2, 3)]
    # point placé exactement sur l'îlot déconnecté
    idx, _ = graph.nearest_indices(np.array([graph.node_array[island[0]]]))
    assert int(idx[0]) not in island


def test_remove_short_loops_cuts_back_and_forth_only():
    from shape_route_experiments_v16 import remove_short_loops
    xy = np.array([[0, 0], [100, 0], [200, 0], [200, 50], [300, 0], [300, 1000], [0, 1000]], dtype=float)
    # 0 -> 1 -> 2 -> 3 (impasse) -> 2 -> 4 : l'aller-retour 2-3-2 (100 m) est supprimé
    assert remove_short_loops([0, 1, 2, 3, 2, 4], xy, 150.0) == [0, 1, 2, 4]
    # une grande boucle (dessin) est conservée
    big = [0, 1, 2, 4, 5, 6, 0, 1]
    assert remove_short_loops(big, xy, 150.0) == big
    # boucles imbriquées
    assert remove_short_loops([0, 1, 2, 1, 2, 1, 0, 1, 2, 4], xy, 450.0) == [0, 1, 2, 4]


@pytest.mark.parametrize("shape", ["heart", "square", "star"])
def test_calibration_reaches_requested_distance(shape):
    """Avec le calibrage de taille, la proposition « distance la plus proche » doit tomber
    à quelques pourcents de la distance demandée, et rester sous le maximum autorisé."""
    from planner_adapter import plan_from_graph
    graph = RoadGraph(random_road_graph(5, n_side=45, step=70.0, oneway_ratio=0.0))
    res = plan_from_graph(graph, 6.0, {"mode": "shape", "shape": shape})
    for route in res["routes"]:
        if "Distance la plus proche" in route["variant"]:
            assert abs(route["total_distance_m"] - 6000.0) <= 0.05 * 6000.0
        assert route["over_max_m"] == 0.0
        # la distance annoncée est bien celle du tracé envoyé (rue par rue)
        pts = np.array(route["segments"][0]["points"])
        assert sum(haversine(a, b) for a, b in zip(pts, pts[1:])) == pytest.approx(route["total_distance_m"], rel=0.01)


def test_route_from_target_returns_connected_path():
    payload = random_road_graph(4, oneway_ratio=0.0)
    graph = RoadGraph(payload)
    target = make_candidate_points(get_base_shape("heart", ""), np.zeros(2), 1200.0, 0.0)
    node_path, route_points, extra = route_from_target(graph, target, sample_count=60)
    assert extra["unreachable_segments"] == 0
    edges = {(e["from"], e["to"]) for e in payload["edges"]} | {(e["to"], e["from"]) for e in payload["edges"]}
    assert all((a, b) in edges for a, b in zip(node_path, node_path[1:]))
    assert len(route_points) >= 2


@pytest.mark.parametrize("drawing", [
    {"mode": "shape", "shape": "square"},
    {"mode": "shape", "shape": "circle"},
    {"mode": "shape", "shape": "heart"},
    {"mode": "shape", "shape": "star"},
    {"mode": "shape", "shape": "infinity"},
    {"mode": "text", "text": "GO"},
])
@pytest.mark.parametrize("distance_m", [5000.0, 15000.0, 30000.0])
def test_required_radius_covers_every_candidate(drawing, distance_m):
    """Le rayon téléchargé doit contenir tous les points de toutes les formes testées,
    pour n'importe quelle orientation du réseau."""
    from shape_route_experiments_v16 import (
        required_radius_m, shape_layout, split_letter_layout, split_letters, make_candidate_points,
    )
    radius = required_radius_m(drawing, distance_m)
    if radius >= distance_m / 2.0:
        return  # rayon plafonné à l'ancienne valeur : comportement inchangé
    margin = 600.0
    text = drawing.get("text", "P2I")
    name = "text" if drawing["mode"] == "text" else drawing["shape"]
    base = get_base_shape(name, text)
    centers, sizes = shape_layout(base, distance_m, name, use_translation=True)
    groups = [(base, centers, sizes)]
    if drawing["mode"] == "text":
        for angle in (0.0, 37.0, 90.0):
            d = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
            n = np.array([-d[1], d[0]])
            groups += [(b, c, s) for _, b, c, s in split_letter_layout(split_letters(text), distance_m, d, n)]
    for b, cs, ss in groups:
        for c in cs:
            for size in ss:
                for angle in range(0, 360, 15):
                    pts = make_candidate_points(b, c, size, angle)
                    assert np.hypot(pts[:, 0], pts[:, 1]).max() <= radius - margin + 1e-6


@pytest.mark.parametrize("street_angle", [-80.0, -37.0, 0.0, 8.0, 45.0, 89.0])
def test_every_orientation_is_explored(street_angle):
    """Chaque forme est testée sur toute sa période de symétrie, avec un pas fin, en incluant
    l'axe des rues ; le texte reste lisible (proche de l'horizontale)."""
    from shape_route_experiments_v16 import ORIENTATION_RULES, TEXT_MAX_TILT_DEG, search_angles, fold_angle

    class FakeGraph:
        _dominant_angle = street_angle

    for shape, (period, step) in ORIENTATION_RULES.items():
        angles = search_angles(FakeGraph, shape)
        assert len(angles) == round(period / step)
        assert any(abs(fold_angle(a - street_angle, period)) < 1e-9 for a in angles)
        # aucun « trou » plus grand que le pas dans la période
        folded = sorted(fold_angle(a, period) for a in angles)
        gaps = np.diff(folded + [folded[0] + period])
        assert gaps.max() <= step + 1e-9
    assert all(abs(a) <= TEXT_MAX_TILT_DEG for a in search_angles(FakeGraph, "text"))
