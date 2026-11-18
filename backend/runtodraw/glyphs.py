"""Glyphes du mode texte : chaque lettre (A-Z) et chiffre est une polyligne simple, tracée par ses traits seuls."""
import numpy as np

from runtodraw.geometry import normalize_points


def _pts(lst):
    return np.array(lst, dtype=float)


GLYPHS = {
    "A": _pts([[0,0],[0.5,1],[1,0],[0.75,0.5],[0.25,0.5]]),
    "B": _pts([[0,0],[0,1],[0.65,1],[0.85,0.85],[0.65,0.65],[0,0.6],[0.65,0.6],[0.9,0.4],[0.65,0.15],[0,0.1]]),
    "C": _pts([[1,0.1],[0.8,0],[0.2,0],[0,0.2],[0,0.8],[0.2,1],[0.8,1],[1,0.9]]),
    "D": _pts([[0,0],[0,1],[0.55,1],[0.9,0.75],[0.9,0.25],[0.55,0],[0,0]]),
    "E": _pts([[1,0],[0,0],[0,1],[1,1],[0,1],[0,0.5],[0.75,0.5]]),
    "F": _pts([[0,0],[0,1],[1,1],[0,1],[0,0.5],[0.75,0.5]]),
    # G : part d'en haut à droite, fait le tour par la gauche, remonte à droite jusqu'au milieu,
    # puis barre vers l'intérieur (l'ancienne version était retournée verticalement).
    "G": _pts([[1,0.8],[0.8,1],[0.2,1],[0,0.8],[0,0.2],[0.2,0],[0.8,0],[1,0.2],[1,0.45],[0.6,0.45]]),
    "H": _pts([[0,0],[0,1],[0,0.5],[1,0.5],[1,1],[1,0]]),
    "I": _pts([[0,1],[1,1],[0.5,1],[0.5,0],[0,0],[1,0]]),
    "J": _pts([[1,1],[1,0.15],[0.8,0],[0.3,0],[0.1,0.2]]),
    "K": _pts([[0,0],[0,1],[0,0.5],[1,1],[0,0.5],[1,0]]),
    "L": _pts([[0,1],[0,0],[1,0]]),
    "M": _pts([[0,0],[0,1],[0.5,0.35],[1,1],[1,0]]),
    "N": _pts([[0,0],[0,1],[1,0],[1,1]]),
    "O": _pts([[0.2,0],[0.8,0],[1,0.2],[1,0.8],[0.8,1],[0.2,1],[0,0.8],[0,0.2],[0.2,0]]),
    "P": _pts([[0,0],[0,1],[0.75,1],[1,0.8],[0.75,0.6],[0,0.6]]),
    "Q": _pts([[0.2,0],[0.8,0],[1,0.2],[1,0.8],[0.8,1],[0.2,1],[0,0.8],[0,0.2],[0.2,0],[0.65,0.35],[1,0]]),
    "R": _pts([[0,0],[0,1],[0.75,1],[1,0.8],[0.75,0.6],[0,0.6],[0.5,0.6],[1,0]]),
    "S": _pts([[1,0.85],[0.8,1],[0.2,1],[0,0.8],[0.2,0.6],[0.8,0.4],[1,0.2],[0.8,0],[0.2,0],[0,0.15]]),
    "T": _pts([[0,1],[1,1],[0.5,1],[0.5,0]]),
    "U": _pts([[0,1],[0,0.2],[0.2,0],[0.8,0],[1,0.2],[1,1]]),
    "V": _pts([[0,1],[0.5,0],[1,1]]),
    "W": _pts([[0,1],[0.2,0],[0.5,0.55],[0.8,0],[1,1]]),
    "X": _pts([[0,1],[1,0],[0.5,0.5],[0,0],[1,1]]),
    "Y": _pts([[0,1],[0.5,0.55],[1,1],[0.5,0.55],[0.5,0]]),
    "Z": _pts([[0,1],[1,1],[0,0],[1,0]]),
    "0": _pts([[0.2,0],[0.8,0],[1,0.2],[1,0.8],[0.8,1],[0.2,1],[0,0.8],[0,0.2],[0.2,0],[0.8,1]]),
    "1": _pts([[0.3,0.8],[0.5,1],[0.5,0],[0.25,0],[0.75,0]]),
    "2": _pts([[0,0.8],[0.2,1],[0.8,1],[1,0.8],[0,0],[1,0]]),
    "3": _pts([[0,0.85],[0.2,1],[0.8,1],[1,0.8],[0.6,0.5],[1,0.2],[0.8,0],[0.2,0],[0,0.15]]),
    "4": _pts([[0.8,0],[0.8,1],[0,0.35],[1,0.35]]),
    "5": _pts([[1,1],[0.2,1],[0.1,0.55],[0.75,0.55],[1,0.3],[0.8,0],[0.2,0],[0,0.15]]),
    "6": _pts([[1,0.85],[0.8,1],[0.25,1],[0,0.6],[0.15,0.1],[0.75,0],[1,0.25],[0.8,0.5],[0.2,0.5]]),
    "7": _pts([[0,1],[1,1],[0.35,0]]),
    "8": _pts([[0.2,0.5],[0,0.75],[0.2,1],[0.8,1],[1,0.75],[0.8,0.5],[0.2,0.5],[0,0.25],[0.2,0],[0.8,0],[1,0.25],[0.8,0.5]]),
    # 9 : le 6 tourné d'un demi-tour (boucle fermée en haut, queue vers le bas) ; l'ancienne
    # version laissait la boucle ouverte et finissait en haut à gauche.
    "9": _pts([[0,0.15],[0.2,0],[0.75,0],[1,0.4],[0.85,0.9],[0.25,1],[0,0.75],[0.2,0.5],[0.8,0.5]]),
}


# Construit une seule polyligne pour le mot complet.
# C’est utilisé quand le texte est traité comme une forme globale.
def simple_text_polyline(text):
    text = (text or "P2I").upper()
    cursor_x = 0.0
    parts = []
    prev_end = None
    for ch in text:
        if ch == " ":
            cursor_x += 0.7
            prev_end = None
            continue
        glyph = GLYPHS.get(ch)
        if glyph is None:
            cursor_x += 1.0
            prev_end = None
            continue
        g = glyph.copy()
        g[:, 0] += cursor_x
        if prev_end is not None:
            parts.append(prev_end)
            parts.append(g[0])
        parts.extend(g)
        prev_end = g[-1]
        cursor_x += 1.35
    if not parts:
        return GLYPHS["P"].copy()
    return normalize_points(np.asarray(parts, dtype=float))


# Renvoie une polyligne normalisée pour une seule lettre.
def single_letter_polyline(ch):
    glyph = GLYPHS.get(ch.upper())
    if glyph is None:
        return None
    return normalize_points(glyph)
