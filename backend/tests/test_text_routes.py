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
