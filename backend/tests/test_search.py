"""Recherche d'angle en deux temps (grossier puis fin) : moins de candidats, mêmes garanties."""
import numpy as np

from runtodraw import search
from runtodraw.search import _neighbours, _start_angles_near, rank_angles


SQUARE = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]])


def candidate(angle, combined, over_max=0.0, under_min=0.0):
    return {"metrics": {"angle_deg": angle, "combined": combined, "over_max": over_max, "under_min": under_min}}


def test_rank_angles_puts_feasible_candidates_first():
    ranked = rank_angles([
        candidate(0.0, 5.0, over_max=300.0),   # meilleur score mais hors tolérance
        candidate(10.0, 9.0),
        candidate(20.0, 7.0),
        candidate(20.0, 12.0),                  # seul le meilleur candidat de chaque angle compte
    ])
    assert ranked == [20.0, 10.0, 0.0]


def test_neighbours_wrap_around_and_skip_chosen():
    angles = [0.0, 10.0, 20.0, 30.0]
    assert _neighbours(angles, [0.0]) == [30.0, 10.0]
    assert _neighbours(angles, [0.0, 10.0]) == [30.0, 20.0]


def test_start_angles_follow_the_best_projection_angles():
    angles = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0]
    assert _start_angles_near(angles, None) == angles
    assert _start_angles_near(angles, [88.0, 31.0, 92.0]) == [90.0, 30.0]
    assert _start_angles_near(angles, [358.0]) == [0.0]   # écart calculé modulo 360°


def test_coarse_pass_evaluates_fewer_angles(monkeypatch):
    """Sur une forme à 36 angles, la projection n'en teste qu'une partie, et la translation reprend les meilleurs."""
    tested = []

    def fake_search(graph, base_points, centers, angles, *args, **kwargs):
        tested.append(list(angles))
        return [candidate(a, abs(a - 100.0)) for a in angles]

    monkeypatch.setattr(search, "calibrated_search", fake_search)
    monkeypatch.setattr(search, "search_angles", lambda graph, shape: [10.0 * k for k in range(36)])
    monkeypatch.setattr(search, "pick_best", lambda evaluated: (evaluated[0], evaluated[0]))

    projection = search.evaluate_method(None, SQUARE, 10000.0, 0.1, "heart", "projection")
    assert sum(len(t) for t in tested) < 36
    assert 100.0 in projection["ranked_angles"]

    tested.clear()
    search.evaluate_method(None, SQUARE, 10000.0, 0.1, "heart", "translation", angle_hint=projection["ranked_angles"])
    assert len(tested[0]) == len(projection["ranked_angles"])
