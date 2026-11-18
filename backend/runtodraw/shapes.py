"""Formes de base (carré, cercle, cœur, étoile, infini) : cibles géométriques idéales,
avant projection sur le vrai réseau routier."""
import math

import numpy as np

from runtodraw.geometry import normalize_points
from runtodraw.glyphs import simple_text_polyline


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
    return normalize_points(pts)


# EN: Selects the base shape requested by the user.
# FR: Sélectionne la forme de base demandée par l’utilisateur.
def get_base_shape(shape_name, text):
    name = shape_name.lower()
    if name == "square":
        return make_square()
    if name == "circle":
        return make_circle()
    if name == "heart":
        return make_heart()
    if name == "star":
        return make_star()
    if name == "infinity":
        return make_infinity()
    if name == "text":
        return simple_text_polyline(text)
    raise ValueError(f"Unknown shape: {shape_name}")
