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


def make_cross():
    w = 0.17  # demi-largeur des branches
    return np.array([
        [-w, 0.5], [w, 0.5], [w, w], [0.5, w], [0.5, -w], [w, -w],
        [w, -0.5], [-w, -0.5], [-w, -w], [-0.5, -w], [-0.5, w], [-w, w], [-w, 0.5],
    ], dtype=float)


def make_arrow():
    # Flèche pleine pointant vers le haut : pointe, ailes, puis tige.
    return np.array([
        [0.0, 0.5], [0.5, 0.0], [0.17, 0.0], [0.17, -0.5], [-0.17, -0.5], [-0.17, 0.0], [-0.5, 0.0], [0.0, 0.5],
    ], dtype=float)


def make_house():
    # Pentagone : un carré surmonté d'un toit à deux pentes.
    return np.array([[-0.4, -0.4], [0.4, -0.4], [0.4, 0.1], [0.0, 0.5], [-0.4, 0.1], [-0.4, -0.4]], dtype=float)


def make_lightning():
    # Éclair : sommet en haut à droite, un décrochement au milieu, pointe en bas à gauche.
    return np.array([
        [0.10, 0.5], [-0.30, -0.05], [-0.02, -0.05], [-0.12, -0.5], [0.32, 0.12], [0.04, 0.12], [0.10, 0.5],
    ], dtype=float)


def make_crescent(n=48):
    # Croissant ouvert vers la droite : grand arc extérieur, puis arc intérieur parcouru en sens inverse.
    big_r, small_r, offset = 0.5, 0.38, 0.22
    x_cut = (offset ** 2 + big_r ** 2 - small_r ** 2) / (2 * offset)   # abscisse des deux pointes
    y_cut = math.sqrt(big_r ** 2 - x_cut ** 2)
    a_out = math.atan2(y_cut, x_cut)
    outer_t = np.linspace(a_out, 2 * math.pi - a_out, n)
    outer = np.column_stack([big_r * np.cos(outer_t), big_r * np.sin(outer_t)])
    a_in = math.atan2(y_cut, x_cut - offset)
    inner_t = np.linspace(2 * math.pi - a_in, a_in, n)
    inner = np.column_stack([offset + small_r * np.cos(inner_t), small_r * np.sin(inner_t)])
    pts = np.vstack([outer, inner])
    pts[-1] = pts[0]
    return pts


def make_drop(n=48):
    # Goutte : pointe en haut, deux tangentes, puis un arc de cercle en bas.
    r, cy, tip = 0.3, -0.2, 0.5
    d = tip - cy
    tangent = math.acos(r / d)                       # angle (au centre) entre la pointe et les points de tangence
    start, end = math.pi / 2 - tangent, math.pi / 2 + tangent
    t = np.linspace(start, end - 2 * math.pi, n)     # de la tangente de droite à celle de gauche, par le bas
    arc = np.column_stack([r * np.cos(t), cy + r * np.sin(t)])
    return np.vstack([[0.0, tip], arc, [0.0, tip]])


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
    if name == "cross":
        return make_cross()
    if name == "arrow":
        return make_arrow()
    if name == "house":
        return make_house()
    if name == "lightning":
        return make_lightning()
    if name == "crescent":
        return make_crescent()
    if name == "drop":
        return make_drop()
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
