"""Tests unitaires du module shapes (formes de base et glyphes de texte)."""
import numpy as np
import pytest

from runtodraw import shapes


@pytest.mark.parametrize("builder", [shapes.make_square, shapes.make_circle, shapes.make_heart, shapes.make_star])
def test_closed_shapes_start_and_end_at_the_same_point(builder):
    pts = builder()
    assert np.allclose(pts[0], pts[-1], atol=1e-9)


def test_make_infinity_is_normalized():
    pts = shapes.make_infinity()
    assert np.allclose(pts.mean(axis=0), 0.0, atol=0.2)
    extent = pts.max(axis=0) - pts.min(axis=0)
    assert np.isclose(extent.max(), 1.0)


def test_glyphs_cover_all_letters_and_digits():
    expected = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    assert set(shapes.GLYPHS.keys()) == expected
    for glyph in shapes.GLYPHS.values():
        assert glyph.ndim == 2 and glyph.shape[1] == 2


def test_single_letter_matches_word_of_one_letter():
    # Pas de segment de liaison à ajouter pour un mot d'une seule lettre :
    # les deux fonctions doivent produire exactement le même tracé.
    assert np.allclose(shapes.single_letter_polyline("a"), shapes.simple_text_polyline("A"))


def test_single_letter_unknown_character_returns_none():
    assert shapes.single_letter_polyline("?") is None


def test_simple_text_polyline_falls_back_to_p_when_no_glyph_matches():
    # Un texte fait uniquement d'espaces ne produit aucun point à tracer.
    assert np.array_equal(shapes.simple_text_polyline("  "), shapes.GLYPHS["P"])


def test_get_base_shape_dispatches_known_shapes():
    assert np.array_equal(shapes.get_base_shape("square", text="P2I"), shapes.make_square())
    assert np.array_equal(shapes.get_base_shape("Circle", text="P2I"), shapes.make_circle())
    assert np.array_equal(shapes.get_base_shape("text", text="RUN"), shapes.simple_text_polyline("RUN"))


def test_get_base_shape_rejects_unknown_shape():
    with pytest.raises(ValueError):
        shapes.get_base_shape("triangle", text="P2I")
