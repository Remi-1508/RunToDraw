"""Dessin libre : transforme les points tracés par l'utilisateur en une forme exploitable par le moteur.

Le dessin arrive tel que le navigateur le fournit (repère d'un canvas : x vers la droite, y vers le BAS,
coordonnées quelconques). `prepare_custom_shape` le nettoie une seule fois, à l'entrée de l'API ; le reste du
code manipule ensuite des points « carte » (y vers le haut) déjà simplifiés, sans y retoucher.
"""
import math

import numpy as np

from runtodraw.geometry import clean_polyline, polyline_length

MAX_RAW_POINTS = 2000        # un tracé à la souris en produit quelques centaines
MAX_COORDINATE = 1e6         # borne arbitraire : évite les valeurs absurdes (et les NaN / infinis)
MAX_SHAPE_POINTS = 150       # après simplification : le moteur rééchantillonne de toute façon à ~70 points
SIMPLIFY_TOLERANCE = 0.012   # écart toléré par la simplification, en fraction de la taille du dessin
CLOSE_TOLERANCE = 0.10       # début et fin plus proches que cela (fraction de la taille) : on ferme la forme
MIN_SIZE_RATIO = 1e-6


def simplify_rdp(points, epsilon):
    """Douglas-Peucker itératif (sans récursion : pas de limite de profondeur sur un long tracé).
    Garde les points qui s'écartent de plus de `epsilon` du segment qui les encadre."""
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        a, b = pts[lo], pts[hi]
        ab = b - a
        norm = math.hypot(*ab)
        seg = pts[lo + 1:hi]
        if norm < 1e-12:
            dist = np.hypot(*(seg - a).T)
        else:
            dist = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / norm
        far = int(np.argmax(dist))
        if dist[far] > epsilon:
            idx = lo + 1 + far
            keep[idx] = True
            stack.extend([(lo, idx), (idx, hi)])
    return pts[keep]


def prepare_custom_shape(raw_points):
    """Points bruts du canvas -> forme nettoyée (liste de [x, y], y vers le haut, centrée sur son milieu).

    Étapes : validation, retournement de l'axe y, suppression des doublons, simplification, fermeture si le
    tracé revient près de son point de départ. Lève ValueError (message affichable) si le dessin est inutilisable.
    """
    try:
        pts = np.asarray(raw_points, dtype=float).reshape(-1, 2)
    except (ValueError, TypeError):
        raise ValueError("Le dessin n'est pas lisible.")
    if len(pts) > MAX_RAW_POINTS:
        raise ValueError("Le dessin contient trop de points.")
    if not np.all(np.isfinite(pts)) or np.abs(pts).max(initial=0.0) > MAX_COORDINATE:
        raise ValueError("Le dessin contient des coordonnées invalides.")

    pts[:, 1] *= -1.0                      # canvas (y vers le bas) -> carte (y vers le haut)
    pts = clean_polyline(pts)
    if len(pts) < 2:
        raise ValueError("Le dessin est trop court : trace une forme un peu plus grande.")

    size = float(max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1])))
    if size < MIN_SIZE_RATIO or polyline_length(pts) < 3 * size * 0.3:
        raise ValueError("Le dessin est trop petit ou trop simple : trace une forme un peu plus grande.")

    pts = simplify_rdp(pts, SIMPLIFY_TOLERANCE * size)
    # Un tracé libre ne revient presque jamais exactement à son point de départ : on referme la forme.
    if len(pts) >= 4 and math.hypot(*(pts[-1] - pts[0])) <= CLOSE_TOLERANCE * size:
        pts[-1] = pts[0]
    if len(pts) < 3:
        raise ValueError("Le dessin est trop simple : ajoute au moins un angle ou une courbe.")
    if len(pts) > MAX_SHAPE_POINTS:   # tracé très tortueux : on resserre la simplification jusqu'à passer sous la limite
        eps = SIMPLIFY_TOLERANCE * size
        while len(pts) > MAX_SHAPE_POINTS:
            eps *= 1.5
            pts = simplify_rdp(pts, eps)

    center = 0.5 * (pts.min(axis=0) + pts.max(axis=0))
    return (pts - center).tolist()
