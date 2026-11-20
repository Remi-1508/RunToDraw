"""Formes de base : cibles géométriques idéales, avant projection sur le vrai réseau routier.
Formes anguleuses (carré, triangle, losange, croix, flèche, maison, éclair) et formes courbes (cercle, cœur,
étoile, infini, croissant, goutte) ; plus le dessin libre de l'utilisateur (voir custom_shape.py).

Toutes les formes sont des contours FERMÉS (premier point = dernier point), centrés sur l'origine :
le moteur les met à l'échelle sur leur boîte englobante, donc seules les proportions comptent."""
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


def make_triangle():
    h = math.sqrt(3) / 2  # triangle équilatéral de côté 1
    return np.array([[-0.5, -h / 3], [0.5, -h / 3], [0.0, 2 * h / 3], [-0.5, -h / 3]], dtype=float)


def make_diamond():
    # Losange un peu plus haut que large (rapport 0,62), pour qu'il ne soit pas confondu avec un carré tourné.
    return np.array([[0.0, 0.5], [0.31, 0.0], [0.0, -0.5], [-0.31, 0.0], [0.0, 0.5]], dtype=float)


def make_lightning():
    # Éclair : sommet en haut à droite, un décrochement au milieu, pointe en bas à gauche.
    return np.array([
        [0.10, 0.5], [-0.30, -0.05], [-0.02, -0.05], [-0.12, -0.5], [0.32, 0.12], [0.04, 0.12], [0.10, 0.5],
    ], dtype=float)


# Sélectionne la forme de base demandée par l’utilisateur.
# `points` : dessin libre déjà préparé (voir custom_shape.prepare_custom_shape), utilisé si shape_name == "custom".
def get_base_shape(shape_name, text, points=None):
    name = shape_name.lower()
    if name == "custom":
        if points is None or len(points) < 3:
            raise ValueError("Dessin libre : points manquants.")
        return np.asarray(points, dtype=float)
    if name == "triangle":
        return make_triangle()
    if name == "diamond":
        return make_diamond()
    if name == "lightning":
        return make_lightning()
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
