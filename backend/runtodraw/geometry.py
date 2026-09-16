"""Fonctions géométriques pures utilisées par tout le moteur.

Deux familles de fonctions :

- les conversions entre coordonnées GPS (lat/lon) et un repère local plan
  en mètres (x vers l'est, y vers le nord), dans lequel les calculs sont
  beaucoup plus simples ;
- les opérations sur les polylignes, c'est-à-dire des tableaux numpy de
  forme (n, 2) représentant une suite de points.

Aucune fonction de ce module ne dépend du graphe routier : elles sont
toutes testables isolément.
"""

import math

import numpy as np

EARTH_RADIUS_M = 6_371_000.0

# Deux points plus proches que ça sont considérés comme identiques.
_EPSILON = 1e-9


# ---------------------------------------------------------------------------
# Conversions de coordonnées
# ---------------------------------------------------------------------------

def latlon_to_xy(lat, lon, lat0, lon0):
    """Projette des coordonnées GPS dans le repère local centré sur (lat0, lon0).

    Projection équirectangulaire : précise à quelques mètres près sur les
    distances d'une course à pied. Accepte des scalaires ou des tableaux numpy.
    """
    x = np.radians(np.asarray(lon) - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    y = np.radians(np.asarray(lat) - lat0) * EARTH_RADIUS_M
    return x, y


def xy_to_latlon(x, y, lat0, lon0):
    """Opération inverse de latlon_to_xy."""
    lat = lat0 + np.degrees(np.asarray(y) / EARTH_RADIUS_M)
    lon = lon0 + np.degrees(np.asarray(x) / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    return lat, lon


def haversine_m(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau en mètres entre deux points GPS."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Opérations sur les polylignes
# ---------------------------------------------------------------------------

def _segment_lengths(pts):
    return np.linalg.norm(np.diff(pts, axis=0), axis=1)


def polyline_length(points):
    """Longueur totale d'une polyligne, en mètres."""
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return 0.0
    return float(_segment_lengths(pts).sum())


def clean_polyline(points):
    """Supprime les points consécutifs confondus."""
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts) < 2:
        return pts.copy()
    keep = np.concatenate([[True], _segment_lengths(pts) > _EPSILON])
    return pts[keep]


def resample_polyline(points, n_samples=120):
    """Redistribue n_samples points à intervalles réguliers le long de la polyligne.

    Indispensable pour comparer deux tracés qui n'ont pas le même nombre de
    points : après rééchantillonnage, le i-ème point de chacun correspond à
    la même fraction du parcours.
    """
    pts = clean_polyline(points)
    if len(pts) == 0:
        return pts
    if len(pts) == 1:
        return np.repeat(pts, n_samples, axis=0)

    cumulative = np.concatenate([[0.0], np.cumsum(_segment_lengths(pts))])
    targets = np.linspace(0.0, cumulative[-1], n_samples)
    return np.column_stack([
        np.interp(targets, cumulative, pts[:, 0]),
        np.interp(targets, cumulative, pts[:, 1]),
    ])


def rotate_points(points, angle_deg):
    """Rotation autour de l'origine, angle en degrés (sens trigonométrique)."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    rotation = np.array([[c, -s], [s, c]])
    return np.asarray(points, dtype=float) @ rotation.T


def _bbox_center_and_extent(pts):
    """Centre de la boîte englobante et son plus grand côté."""
    mins, maxs = pts.min(axis=0), pts.max(axis=0)
    extent = max(maxs[0] - mins[0], maxs[1] - mins[1], _EPSILON)
    return (mins + maxs) / 2, extent


def fit_points(points, center, size_m):
    """Place la forme autour de center, avec un plus grand côté de size_m mètres."""
    pts = np.asarray(points, dtype=float)
    if len(pts) == 0:
        return pts.copy()
    bbox_center, extent = _bbox_center_and_extent(pts)
    return (pts - bbox_center) * (size_m / extent) + np.asarray(center, dtype=float)


def normalize_points(points):
    """Centre la forme sur l'origine et la ramène dans un carré de côté 1."""
    return fit_points(points, (0.0, 0.0), 1.0)


def _turn_angles_deg(pts):
    """Angle (en degrés) du changement de direction à chaque point intérieur."""
    vectors = np.diff(pts, axis=0)
    before, after = vectors[:-1], vectors[1:]
    norms = np.linalg.norm(before, axis=1) * np.linalg.norm(after, axis=1)
    cos = np.einsum("ij,ij->i", before, after) / np.maximum(norms, _EPSILON)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def simplify_path_points(points, angle_tol_deg=8.0):
    """Retire les points où la direction change de moins de angle_tol_deg.

    La direction est mesurée depuis le dernier point conservé, ce qui évite
    qu'une courbe douce soit entièrement effacée petit à petit.
    """
    pts = clean_polyline(points)
    if len(pts) < 3:
        return pts

    kept = [pts[0]]
    for current, following in zip(pts[1:-1], pts[2:]):
        incoming = current - kept[-1]
        outgoing = following - current
        norms = np.linalg.norm(incoming) * np.linalg.norm(outgoing)
        if norms < _EPSILON:
            continue
        cos = np.clip(np.dot(incoming, outgoing) / norms, -1.0, 1.0)
        if math.degrees(math.acos(cos)) > angle_tol_deg:
            kept.append(current)
    kept.append(pts[-1])
    return np.asarray(kept)


def turn_penalty(points, free_angle_deg=35.0):
    """Pénalité moyenne des virages serrés.

    Chaque changement de direction au-delà de free_angle_deg coûte
    (angle - free_angle_deg). Un tracé fluide obtient donc un score proche de 0.
    """
    pts = clean_polyline(points)
    if len(pts) < 3:
        return 0.0
    excess = np.maximum(_turn_angles_deg(pts) - free_angle_deg, 0.0)
    return float(excess.sum() / (len(pts) - 2))
