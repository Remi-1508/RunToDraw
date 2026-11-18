"""Géométrie 2D : conversions GPS <-> repère local en mètres, rééchantillonnage, rotation,
mise à l'échelle et simplification de polylignes."""
import math

import numpy as np


# Convertit la latitude/longitude en un repère local x/y en mètres.
# Cela simplifie les opérations géométriques par rapport à un travail direct en coordonnées GPS.
def latlon_to_xy_m(lat, lon, lat0, lon0):
    r = 6371000.0
    x = math.radians(lon - lon0) * r * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * r
    return x, y


# Calcule la longueur totale d’une polyligne.
def polyline_length(points):
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return 0.0
    diffs = pts[1:] - pts[:-1]
    return float(np.linalg.norm(diffs, axis=1).sum())


# Supprime les points consécutifs identiques.
# Cela évite des points inutiles avant le rééchantillonnage ou l’évaluation.
def clean_polyline(points):
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts) == 0:
        return np.empty((0, 2), dtype=float)
    # Vectorisé : on garde un point s'il diffère du précédent.
    step = np.hypot(*(pts[1:] - pts[:-1]).T)
    keep = np.concatenate([[True], step > 1e-9])
    return pts[keep]

# Rééchantillonne une polyligne avec un nombre fixe de points.
# C’est utile pour comparer deux chemins de manière équitable,
# même s’ils n’ont pas à l’origine le même nombre de points.
def resample_polyline(points, n_samples=120):
    pts = clean_polyline(points)
    if len(pts) == 0:
        return pts
    if len(pts) == 1:
        return np.repeat(pts, n_samples, axis=0)

    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    total = float(seg.sum())
    if total <= 1e-12:
        return np.repeat(pts[:1], n_samples, axis=0)

    # Interpolation linéaire le long de la longueur cumulée (vectorisée avec np.interp).
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, total, n_samples)
    return np.column_stack([np.interp(targets, cum, pts[:, 0]), np.interp(targets, cum, pts[:, 1])])

# Applique une rotation 2D à un ensemble de points.
def rotate_points(points, angle_deg):
    pts = np.asarray(points, dtype=float)
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    r = np.array([[c, -s], [s, c]], dtype=float)
    return pts @ r.T


# Normalise une forme pour qu’elle soit centrée et mise à l’échelle de façon cohérente.
# Cela permet de réutiliser plus facilement le même générateur de forme avec des tailles différentes ensuite.
def normalize_points(points):
    pts = np.asarray(points, dtype=float).copy()
    if len(pts) == 0:
        return pts
    xmin, ymin = np.min(pts, axis=0)
    xmax, ymax = np.max(pts, axis=0)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    w = max(xmax - xmin, 1e-9)
    h = max(ymax - ymin, 1e-9)
    pts[:, 0] = (pts[:, 0] - cx) / max(w, h)
    pts[:, 1] = (pts[:, 1] - cy) / max(w, h)
    return pts


# Met à l’échelle et place une forme normalisée autour d’un centre choisi.
def fit_points(points, center, size_m):
    pts = np.asarray(points, dtype=float).copy()
    if len(pts) == 0:
        return pts
    xmin, ymin = np.min(pts, axis=0)
    xmax, ymax = np.max(pts, axis=0)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    w = max(xmax - xmin, 1e-9)
    h = max(ymax - ymin, 1e-9)
    scale = size_m / max(w, h)
    pts[:, 0] = (pts[:, 0] - cx) * scale + center[0]
    pts[:, 1] = (pts[:, 1] - cy) * scale + center[1]
    return pts


# Simplifie un trajet calculé en supprimant les points qui ne créent pas
# un changement de direction suffisamment fort.
# Cela réduit le bruit visuel après la reconstruction par plus court chemin.
def simplify_path_points(points, angle_tol_deg=8.0):
    pts = clean_polyline(points)
    if len(pts) < 3:
        return pts
    # Séquentiel par nature (chaque test dépend du dernier point gardé) : on utilise des
    # flottants Python simples, bien plus rapides que des appels NumPy sur des points isolés.
    coords = pts.tolist()
    keep_idx = [0]
    ax, ay = coords[0]
    for i in range(1, len(coords) - 1):
        bx, by = coords[i]
        cx, cy = coords[i + 1]
        abx, aby = bx - ax, by - ay
        bcx, bcy = cx - bx, cy - by
        nab = math.hypot(abx, aby)
        nbc = math.hypot(bcx, bcy)
        if nab < 1e-9 or nbc < 1e-9:
            continue
        cosang = (abx * bcx + aby * bcy) / (nab * nbc)
        cosang = min(1.0, max(-1.0, cosang))
        if math.degrees(math.acos(cosang)) > angle_tol_deg:
            keep_idx.append(i)
            ax, ay = bx, by
    keep_idx.append(len(coords) - 1)
    return pts[keep_idx]

# Calcule l’angle entre deux vecteurs.
def angle_between(v1, v2):
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    c = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return math.degrees(math.acos(c))


# Mesure à quel point un trajet contient beaucoup de virages.
# Cela pénalise les trajets avec beaucoup de changements de direction marqués.
def path_turn_penalty(points):
    pts = clean_polyline(points)
    if len(pts) < 3:
        return 0.0
    # Angle en chaque point intérieur, calculé pour tous les points d'un coup.
    a = pts[1:-1] - pts[:-2]
    b = pts[2:] - pts[1:-1]
    na = np.hypot(a[:, 0], a[:, 1])
    nb = np.hypot(b[:, 0], b[:, 1])
    valid = (na >= 1e-9) & (nb >= 1e-9)
    cosang = np.ones(len(a))
    cosang[valid] = np.einsum("ij,ij->i", a[valid], b[valid]) / (na[valid] * nb[valid])
    ang = np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))
    total = float(np.sum(np.maximum(ang - 35.0, 0.0)))
    return total / max(len(pts) - 2, 1)


def fold_angle(angle_deg, period_deg):
    """Ramène un angle dans [-période/2, période/2[."""
    return ((angle_deg + period_deg / 2.0) % period_deg) - period_deg / 2.0


def is_closed(points, tol_ratio=1e-6):
    pts = np.asarray(points, dtype=float)
    span = float(np.ptp(pts, axis=0).max()) if len(pts) else 0.0
    return len(pts) > 2 and float(np.hypot(*(pts[0] - pts[-1]))) <= tol_ratio * max(span, 1.0)


def point_at_fraction(points, fraction):
    """Point du contour situé à `fraction` (0..1) de sa longueur, et indice du segment."""
    pts = np.asarray(points, dtype=float)
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    t = fraction * cum[-1]
    j = int(np.clip(np.searchsorted(cum, t, side="right") - 1, 0, len(seg) - 1))
    alpha = 0.0 if seg[j] <= 0 else (t - cum[j]) / seg[j]
    return pts[j] + alpha * (pts[j + 1] - pts[j]), j


def rotate_closed_outline(points, fraction):
    """Contour fermé réordonné pour commencer (et finir) au point situé à `fraction` de sa longueur."""
    pts = np.asarray(points, dtype=float)
    p, j = point_at_fraction(pts, fraction)
    ring = pts[:-1]  # sans le point final dupliqué
    rest = np.vstack([ring[j + 1:], ring[: j + 1]])
    return np.vstack([p, rest, p])


# Le générateur d’itinéraires travaille en interne avec un repère local x/y.
# Cette fonction reconvertit un point en latitude/longitude pour que le frontend
# puisse afficher le trajet sur la vraie carte.
def xy_to_latlon_m(x, y, lat0, lon0):
    r = 6371000.0
    lat = lat0 + math.degrees(y / r)
    lon = lon0 + math.degrees(x / (r * math.cos(math.radians(lat0))))
    return lat, lon
