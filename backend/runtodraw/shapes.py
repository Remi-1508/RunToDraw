"""Formes de base et glyphes de texte utilisés comme cibles de dessin.

Une forme est toujours une polyligne (tableau numpy de forme (n, 2)) dans un
repère abstrait, avant d'être mise à l'échelle et projetée sur le graphe
routier réel par `graph.RoadGraph` et les fonctions de recherche.
"""

import math

import numpy as np

from . import geometry as geo


# ---------------------------------------------------------------------------
# Formes géométriques
# ---------------------------------------------------------------------------

def make_square():
    return np.array([
        [-0.5, -0.5],
        [0.5, -0.5],
        [0.5, 0.5],
        [-0.5, 0.5],
        [-0.5, -0.5],
    ], dtype=float)


def make_circle(n=220):
    t = np.linspace(0, 2 * np.pi, n)
    return np.column_stack([0.5 * np.cos(t), 0.5 * np.sin(t)])


def make_heart(n=220):
    t = np.linspace(0, 2 * np.pi, n)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    pts = np.column_stack([x, y])
    pts[:, 0] /= max(np.max(np.abs(pts[:, 0])) * 2.0, 1e-9)
    pts[:, 1] /= max(np.max(np.abs(pts[:, 1])) * 2.0, 1e-9)
    return pts


def make_star():
    outer = 0.5
    inner = 0.22
    pts = []
    for i in range(10):
        ang = math.radians(90 + i * 36)
        r = outer if i % 2 == 0 else inner
        pts.append([r * math.cos(ang), r * math.sin(ang)])
    pts.append(pts[0])
    return np.array(pts, dtype=float)


def make_infinity(n=220):
    t = np.linspace(0, 2 * np.pi, n)
    x = 0.55 * np.sin(t)
    y = 0.32 * np.sin(t) * np.cos(t)
    pts = np.column_stack([x, y])
    return geo.normalize_points(pts)


# ---------------------------------------------------------------------------
# Glyphes de texte : chaque lettre ou chiffre est une polyligne simple,
# dessinée dans un carré unité, ce qui permet de les enchaîner et de les
# redimensionner facilement.
# ---------------------------------------------------------------------------

def _pts(lst):
    return np.array(lst, dtype=float)


GLYPHS = {
    "A": _pts([[0,0],[0.5,1],[1,0],[0.75,0.5],[0.25,0.5]]),
    "B": _pts([[0,0],[0,1],[0.65,1],[0.85,0.85],[0.65,0.65],[0,0.6],[0.65,0.6],[0.9,0.4],[0.65,0.15],[0,0.1]]),
    "C": _pts([[1,0.1],[0.8,0],[0.2,0],[0,0.2],[0,0.8],[0.2,1],[0.8,1],[1,0.9]]),
    "D": _pts([[0,0],[0,1],[0.55,1],[0.9,0.75],[0.9,0.25],[0.55,0],[0,0]]),
    "E": _pts([[1,0],[0,0],[0,1],[1,1],[0,1],[0,0.5],[0.75,0.5]]),
    "F": _pts([[0,0],[0,1],[1,1],[0,1],[0,0.5],[0.75,0.5]]),
    "G": _pts([[1,0.2],[0.8,0],[0.2,0],[0,0.2],[0,0.8],[0.2,1],[0.8,1],[1,0.8],[1,0.55],[0.6,0.55]]),
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
    "9": _pts([[0.85,0.45],[0.7,0],[0.2,0],[0,0.2],[0.2,0.5],[0.8,0.5],[1,0.85],[0.8,1],[0.2,1],[0,0.8]]),
}


def simple_text_polyline(text):
    """Une seule polyligne pour le mot entier (mode "mot complet").

    Les lettres sont posées côte à côte puis reliées par un segment, de
    sorte que le mot forme un unique tracé continu avant normalisation.
    """
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
    return geo.normalize_points(np.asarray(parts, dtype=float))


def single_letter_polyline(ch):
    """Polyligne normalisée d'une seule lettre (mode "lettres indépendantes")."""
    glyph = GLYPHS.get(ch.upper())
    if glyph is None:
        return None
    return geo.normalize_points(glyph)


# ---------------------------------------------------------------------------
# Sélection de la forme demandée par l'utilisateur
# ---------------------------------------------------------------------------

_SHAPE_BUILDERS = {
    "square": make_square,
    "circle": make_circle,
    "heart": make_heart,
    "star": make_star,
    "infinity": make_infinity,
}


def get_base_shape(shape_name, text):
    """Renvoie la polyligne cible pour shape_name (et text si shape_name == "text")."""
    name = shape_name.lower()
    if name == "text":
        return simple_text_polyline(text)
    builder = _SHAPE_BUILDERS.get(name)
    if builder is None:
        raise ValueError(f"Unknown shape: {shape_name}")
    return builder()
