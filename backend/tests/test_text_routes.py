"""Mise en page du mode texte : les lettres d'un mot doivent avoir la même hauteur."""
import numpy as np
import pytest

from runtodraw.glyphs import single_letter_polyline
from runtodraw.geometry import polyline_length
from runtodraw.text_routes import letter_target_distances, split_letter_layout


def test_la_moyenne_des_distances_visees_reste_la_distance_demandee():
    targets = letter_target_distances(["F", "C", "B"], 10_000.0)
    assert sum(targets) / 3 == pytest.approx(10_000.0, rel=0.02)


def test_une_lettre_courte_vise_moins_qu_une_lettre_longue():
    # Le C se trace en moins de longueur que le F pour la même hauteur : sa distance visée est donc plus petite.
    f, c, b = letter_target_distances(["F", "C", "B"], 10_000.0)
    assert c < f and c < b


def test_les_lettres_ont_la_meme_taille_nominale():
    """taille nominale = distance visée / longueur du glyphe : identique pour toutes les lettres (hors I et 1)."""
    layout = split_letter_layout(["F", "C", "B"], 10_000.0, np.array([1.0, 0.0]), np.array([0.0, 1.0]))
    nominals = []
    for ch, base, _centers, sizes, target in layout:
        nominals.append(target / polyline_length(base))
        assert target == pytest.approx(10_000.0, rel=0.45)
    assert max(nominals) / min(nominals) < 1.05


def test_une_seule_lettre_garde_la_distance_demandee():
    assert letter_target_distances(["C"], 8_000.0) == [pytest.approx(8_000.0)]


# ---------- Jonction de lettres modifiées à la main ----------

def test_link_letter_routes_keeps_edited_letters_and_stays_continuous():
    from runtodraw import route_editing as ed
    from runtodraw.road_graph import RoadGraph
    from runtodraw.text_routes import link_letter_routes
    from tests.test_road_graph import random_road_graph

    graph = RoadGraph(random_road_graph(3, n_side=40, step=70.0, oneway_ratio=0.0))
    letters = []
    for label, nodes in (("A", [100, 130, 200]), ("B", [600, 640, 700]), ("C", [1100, 1140, 1200])):
        path, anchors = ed.connect(graph, nodes)
        letters.append({"letter": label, "node_path": [graph.node_ids[i] for i in path], "anchor_idx": anchors})

    pieces, total = link_letter_routes(graph, letters)
    assert [p["kind"] for p in pieces] == ["letter", "link", "letter", "link", "letter"]
    for a, b in zip(pieces[:-1], pieces[1:]):
        assert a["node_path"][-1] == b["node_path"][0]
    # Chaque lettre contient son tracé d'origine (éventuellement retourné), sans interruption ni saut.
    by_label = {p["letter"]: p for p in pieces if p["kind"] == "letter"}
    for r in letters:
        expected = [graph._idx_of[n] for n in r["node_path"]]
        walk = by_label[r["letter"]]["node_path"]
        main = walk[by_label[r["letter"]]["anchors"][0]:][:len(expected)]
        assert main in (expected, expected[::-1])
        assert len(set(walk)) >= len(set(expected))
    # Soulignement : chaque lettre commence à son coin bas-gauche et finit à son coin bas-droit.
    from runtodraw.text_routes import _corner_index
    for r in letters:
        original = [graph._idx_of[n] for n in r["node_path"]]
        walk = by_label[r["letter"]]["node_path"]
        assert walk[0] == original[_corner_index(graph, original, right=False)]
        assert walk[-1] == original[_corner_index(graph, original, right=True)]
    assert total > 0
