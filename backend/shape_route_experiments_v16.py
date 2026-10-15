import argparse
import heapq
import json
import math
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components
from scipy.spatial import cKDTree


# EN: matplotlib is only needed for the experiment plots (command line), not by the API.
# Importing it lazily keeps the backend lighter and faster to start.
# FR: matplotlib ne sert qu'aux tracés d'expérimentation (ligne de commande), pas à l'API.
# On l'importe à la demande pour alléger le backend et accélérer son démarrage.
def _plt():
    import matplotlib.pyplot as plt
    return plt


# ============================================================
# EN:
# RunToDraw - V16
# This file contains the main route generation logic.
# It takes a road graph, builds target shapes or letters,
# projects them on the graph, and evaluates which routes
# best match the requested drawing and distance.
#
# In text split mode, each letter receives the FULL requested distance.
# Example: text="P2I", distance=15000
#          => P ~ 15 km, 2 ~ 15 km, I ~ 15 km
#
# FR:
# RunToDraw - V16
# Ce fichier contient la logique principale de génération d’itinéraires.
# Il prend un graphe routier, construit des formes ou des lettres cibles,
# les projette sur le graphe, puis évalue quels trajets correspondent
# le mieux au dessin demandé et à la distance demandée.
#
# En mode texte séparé, chaque lettre reçoit la distance complète demandée.
# Exemple : text="P2I", distance=15000
#           => P ~ 15 km, 2 ~ 15 km, I ~ 15 km
# ============================================================


# EN: Converts latitude/longitude into a local x/y system in meters.
# This makes geometric operations easier than working directly in GPS coordinates.
# FR: Convertit la latitude/longitude en un repère local x/y en mètres.
# Cela simplifie les opérations géométriques par rapport à un travail direct en coordonnées GPS.
def latlon_to_xy_m(lat, lon, lat0, lon0):
    r = 6371000.0
    x = math.radians(lon - lon0) * r * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * r
    return x, y


# EN: Computes the total length of a polyline.
# FR: Calcule la longueur totale d’une polyligne.
def polyline_length(points):
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return 0.0
    diffs = pts[1:] - pts[:-1]
    return float(np.linalg.norm(diffs, axis=1).sum())


# EN: Removes consecutive duplicate points.
# This avoids useless points before resampling or scoring.
# FR: Supprime les points consécutifs identiques.
# Cela évite des points inutiles avant le rééchantillonnage ou l’évaluation.
def clean_polyline(points):
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts) == 0:
        return np.empty((0, 2), dtype=float)
    # EN: Vectorized: keep a point when it differs from the previous one.
    # FR: Vectorisé : on garde un point s'il diffère du précédent.
    step = np.hypot(*(pts[1:] - pts[:-1]).T)
    keep = np.concatenate([[True], step > 1e-9])
    return pts[keep]

# EN: Resamples a polyline with a fixed number of points.
# This is useful to compare two paths fairly, even if they originally
# have different numbers of points.
# FR: Rééchantillonne une polyligne avec un nombre fixe de points.
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

    # EN: Linear interpolation along the cumulative length (vectorized with np.interp).
    # FR: Interpolation linéaire le long de la longueur cumulée (vectorisée avec np.interp).
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, total, n_samples)
    return np.column_stack([np.interp(targets, cum, pts[:, 0]), np.interp(targets, cum, pts[:, 1])])

# EN: Applies a 2D rotation to a set of points.
# FR: Applique une rotation 2D à un ensemble de points.
def rotate_points(points, angle_deg):
    pts = np.asarray(points, dtype=float)
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    r = np.array([[c, -s], [s, c]], dtype=float)
    return pts @ r.T


# EN: Normalizes a shape so that it is centered and scaled consistently.
# This makes it easier to reuse the same shape generator with different sizes later.
# FR: Normalise une forme pour qu’elle soit centrée et mise à l’échelle de façon cohérente.
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


# EN: Scales and places a normalized shape around a chosen center.
# FR: Met à l’échelle et place une forme normalisée autour d’un centre choisi.
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


# EN: Simplifies a computed route by removing points that do not create a strong enough direction change.
# This helps reduce visual noise after shortest-path reconstruction.
# FR: Simplifie un trajet calculé en supprimant les points qui ne créent pas
# un changement de direction suffisamment fort.
# Cela réduit le bruit visuel après la reconstruction par plus court chemin.
def simplify_path_points(points, angle_tol_deg=8.0):
    pts = clean_polyline(points)
    if len(pts) < 3:
        return pts
    # EN: Sequential by nature (each test depends on the last kept point), so we use plain
    # Python floats, which are much faster than NumPy calls on single points.
    # FR: Séquentiel par nature (chaque test dépend du dernier point gardé) : on utilise des
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

# EN: Computes the angle between two vectors.
# FR: Calcule l’angle entre deux vecteurs.
def angle_between(v1, v2):
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    c = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return math.degrees(math.acos(c))


# EN: Measures how "turn-heavy" a route is.
# It penalizes routes with many strong direction changes.
# FR: Mesure à quel point un trajet contient beaucoup de virages.
# Cela pénalise les trajets avec beaucoup de changements de direction marqués.
def path_turn_penalty(points):
    pts = clean_polyline(points)
    if len(pts) < 3:
        return 0.0
    # EN: Angle at every interior point, computed for all points at once.
    # FR: Angle en chaque point intérieur, calculé pour tous les points d'un coup.
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

# EN:
# This class rebuilds the road graph from the exported JSON format.
# Performance-oriented layout:
# - nodes are re-indexed 0..N-1 and stored in a NumPy array (local x/y in meters),
# - a KD-tree finds the nearest node in O(log N) instead of scanning all nodes,
# - adjacency is stored in CSR form (flat arrays) for a fast A* search,
# - strongly connected components tell instantly when a node cannot be reached,
#   instead of exploring the whole graph to find out.
# The public methods keep working with OpenStreetMap node IDs, as before.
#
# FR:
# Cette classe reconstruit le graphe routier à partir du format JSON exporté.
# Organisation pensée pour la performance :
# - les nœuds sont réindexés 0..N-1 et rangés dans un tableau NumPy (x/y locaux en mètres),
# - un KD-tree trouve le nœud le plus proche en O(log N) au lieu de parcourir tous les nœuds,
# - l'adjacence est stockée au format CSR (tableaux plats) pour un A* rapide,
# - les composantes fortement connexes indiquent immédiatement qu'un nœud est injoignable,
#   au lieu d'explorer tout le graphe pour s'en rendre compte.
# Les méthodes publiques continuent de travailler avec les identifiants OSM, comme avant.
class RoadGraph:
    def __init__(self, data):
        self.meta = data["meta"]
        self.nodes = data["nodes"]
        self.edges = data["edges"]
        self.center_lat, self.center_lon = self.meta["center"]

        # --- Nœuds : identifiants OSM -> indices 0..N-1, coordonnées x/y vectorisées ---
        self.node_ids = [n["id"] for n in self.nodes]
        self._idx_of = {nid: i for i, nid in enumerate(self.node_ids)}
        lat = np.fromiter((n["lat"] for n in self.nodes), dtype=float, count=len(self.nodes))
        lon = np.fromiter((n["lon"] for n in self.nodes), dtype=float, count=len(self.nodes))
        r = 6371000.0
        xs = np.radians(lon - self.center_lon) * r * math.cos(math.radians(self.center_lat))
        ys = np.radians(lat - self.center_lat) * r
        self.node_array = np.column_stack([xs, ys])
        self._node_xy_dict = None

        # --- Arcs orientés, dans le même ordre que l'ancienne liste d'adjacence ---
        # (une arête à double sens donne deux arcs : u->v puis v->u)
        src, dst, w = [], [], []
        idx_of = self._idx_of
        for e in self.edges:
            u = idx_of.get(e["from"])
            v = idx_of.get(e["to"])
            if u is None or v is None:
                continue  # arête vers un nœud inconnu : inutilisable
            length = float(e.get("length_m", 0.0))
            src.append(u); dst.append(v); w.append(length)
            if not e.get("oneway", False):
                src.append(v); dst.append(u); w.append(length)
        src = np.asarray(src, dtype=np.int64)
        dst = np.asarray(dst, dtype=np.int64)
        w = np.asarray(w, dtype=float)
        n = len(self.node_ids)

        # EN: CSR layout. A stable sort by source keeps each node's neighbours in insertion order,
        # so ties are explored in the same order as the previous adjacency list.
        # FR: Format CSR. Un tri stable par source conserve l'ordre d'insertion des voisins de chaque nœud,
        # donc les égalités sont explorées dans le même ordre qu'avec l'ancienne liste d'adjacence.
        order = np.argsort(src, kind="stable")
        self._arc_src, self._arc_dst, self._arc_w = src, dst, w  # ordre d'insertion d'origine
        counts = np.bincount(src, minlength=n)
        indptr = np.zeros(n + 1, dtype=np.int64)
        np.cumsum(counts, out=indptr[1:])
        # Listes Python : l'accès élément par élément y est plus rapide que sur des tableaux NumPy.
        self._indptr = indptr.tolist()
        self._indices = dst[order].tolist()
        self._weights = w[order].tolist()
        self._xs = xs.tolist()
        self._ys = ys.tolist()

        # EN: A* heuristic = straight-line distance in the local plane, scaled by k so that it never
        # exceeds the real edge length (haversine). This keeps A* exact (same optimal cost as Dijkstra).
        # FR: Heuristique A* = distance à vol d'oiseau dans le plan local, multipliée par k pour qu'elle
        # ne dépasse jamais la vraie longueur d'arête (haversine). A* reste ainsi exact (même coût optimal que Dijkstra).
        if len(w):
            planar = np.hypot(xs[dst] - xs[src], ys[dst] - ys[src])
            ok = planar > 1e-9
            ratio = float(np.min(w[ok] / planar[ok])) if np.any(ok) else 1.0
            self._h_scale = max(0.0, min(1.0, ratio) * 0.999)
        else:
            self._h_scale = 0.0

        # EN: Strongly connected components + their condensation (a DAG) give exact reachability.
        # FR: Composantes fortement connexes + leur graphe condensé (acyclique) donnent l'accessibilité exacte.
        adj_matrix = csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(n, n))
        _, self._scc = connected_components(adj_matrix, directed=True, connection="strong")
        cs, cd = self._scc[src], self._scc[dst]
        between = cs != cd
        n_scc = int(self._scc.max()) + 1 if n else 0
        self._condensed = csr_matrix(
            (np.ones(int(between.sum()), dtype=np.int8), (cs[between], cd[between])),
            shape=(n_scc, n_scc),
        )
        self._reach_cache = {}

        # EN: Snapping only targets the largest strongly connected component (the main road network).
        # Small isolated pieces (parking aisles, private bits cut by the extraction) can never be
        # reached from the rest: snapping onto them used to create jumps in the route.
        # The KD-tree is built once per graph, then queried for every sampled point of every candidate.
        # FR: L'accroche ne vise que la plus grande composante fortement connexe (le réseau principal).
        # Les petits morceaux isolés (allées de parking, bouts coupés par l'extraction) ne sont jamais
        # accessibles depuis le reste : s'y accrocher créait des sauts dans le trajet.
        # Le KD-tree est construit une fois par graphe, puis interrogé pour chaque point de chaque candidat.
        if n:
            main_component = int(np.argmax(np.bincount(self._scc)))
            self._snap_idx = np.flatnonzero(self._scc == main_component)
        else:
            self._snap_idx = np.arange(0)
        self._kdtree = cKDTree(self.node_array[self._snap_idx])

        self.bounds = {
            "xmin": float(xs.min()),
            "xmax": float(xs.max()),
            "ymin": float(ys.min()),
            "ymax": float(ys.max()),
        }
        self._sp_cache = {}
        self._dominant_angle = None

    # EN: ID -> x/y dictionary, built only if someone asks for it (plots).
    # FR: Dictionnaire identifiant -> x/y, construit seulement si on en a besoin (tracés).
    @property
    def node_xy(self):
        if self._node_xy_dict is None:
            self._node_xy_dict = {nid: self.node_array[i] for i, nid in enumerate(self.node_ids)}
        return self._node_xy_dict

    # EN: Finds the nearest node of the main road network to a target point (KD-tree query).
    # FR: Trouve le nœud du réseau principal le plus proche d'un point cible (requête KD-tree).
    def nearest_node(self, point):
        d, k = self._kdtree.query(np.asarray(point, dtype=float))
        return self.node_ids[int(self._snap_idx[int(k)])], float(d)

    # EN: Vectorized version: all the points of a shape in a single call. Returns node indices.
    # FR: Version vectorisée : tous les points d'une forme en un seul appel. Renvoie des indices de nœuds.
    def nearest_indices(self, points):
        d, k = self._kdtree.query(np.asarray(points, dtype=float))
        return self._snap_idx[np.asarray(k, dtype=np.int64)], np.asarray(d, dtype=float)

    # EN: True if `goal` can be reached from `start` (one BFS per source component, cached).
    # FR: Vrai si `goal` est accessible depuis `start` (un parcours par composante source, mis en cache).
    def _reachable(self, s, g):
        cs, cg = int(self._scc[s]), int(self._scc[g])
        if cs == cg:
            return True
        reach = self._reach_cache.get(cs)
        if reach is None:
            order = breadth_first_order(self._condensed, cs, directed=True, return_predecessors=False)
            reach = np.zeros(self._condensed.shape[0], dtype=bool)
            reach[order] = True
            self._reach_cache[cs] = reach
        return bool(reach[cg])

    # EN: Exact A* shortest path between two node indices. Returns (index path, cost).
    # FR: Plus court chemin A* exact entre deux indices de nœuds. Renvoie (chemin d'indices, coût).
    def shortest_path_idx(self, s, g):
        if s == g:
            return [s], 0.0
        key = (s, g)
        cached = self._sp_cache.get(key)
        if cached is not None:
            return cached
        if not self._reachable(s, g):
            out = (None, float("inf"))
            self._sp_cache[key] = out
            return out

        indptr, indices, weights = self._indptr, self._indices, self._weights
        xs, ys, k = self._xs, self._ys, self._h_scale
        gx, gy = xs[g], ys[g]
        hypot, heappush, heappop = math.hypot, heapq.heappush, heapq.heappop
        inf = float("inf")

        dist = {s: 0.0}
        prev = {}
        pq = [(k * hypot(xs[s] - gx, ys[s] - gy), 0.0, s)]
        while pq:
            _, d, u = heappop(pq)
            if u == g:
                break
            if d > dist[u]:
                continue
            for i in range(indptr[u], indptr[u + 1]):
                v = indices[i]
                nd = d + weights[i]
                if nd < dist.get(v, inf):
                    dist[v] = nd
                    prev[v] = u
                    heappush(pq, (nd + k * hypot(xs[v] - gx, ys[v] - gy), nd, v))

        path = [g]
        cur = g
        while cur != s:
            cur = prev[cur]
            path.append(cur)
        path.reverse()
        out = (path, dist[g])
        self._sp_cache[key] = out
        return out

    # EN: Same as before: shortest path between two OSM node IDs.
    # FR: Comme avant : plus court chemin entre deux identifiants de nœuds OSM.
    def shortest_path(self, start, goal):
        path, cost = self.shortest_path_idx(self._idx_of[start], self._idx_of[goal])
        if path is None:
            return None, cost
        return [self.node_ids[i] for i in path], cost

    # EN: Converts a node path (OSM IDs) into x/y points.
    # FR: Convertit un chemin de nœuds (identifiants OSM) en points x/y.
    def path_to_points(self, node_path):
        return self.node_array[[self._idx_of[nid] for nid in node_path]]


# ============================================================
# EN: Shape generators.
# These functions build the ideal geometric targets before they are projected
# onto the real road graph.
#
# FR: Générateurs de formes.
# Ces fonctions construisent les formes géométriques idéales avant qu’elles
# soient projetées sur le vrai graphe routier.
# ============================================================

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


# ============================================================
# EN:
# Text glyphs.
# Each letter or digit is represented by a simple polyline.
# This keeps the text mode easy to control and easy to scale.
#
# FR:
# Glyphes de texte.
# Chaque lettre ou chiffre est représenté par une polyligne simple.
# Cela permet de garder le mode texte simple à contrôler et simple à redimensionner.
# ============================================================

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


# EN: Builds one single polyline for the whole word.
# This is used when the text is treated as one global shape.
# FR: Construit une seule polyligne pour le mot complet.
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


# EN: Returns one normalized polyline for one single letter.
# FR: Renvoie une polyligne normalisée pour une seule lettre.
def single_letter_polyline(ch):
    glyph = GLYPHS.get(ch.upper())
    if glyph is None:
        return None
    return normalize_points(glyph)


# ============================================================
# EN:
# Scoring.
# These functions evaluate how good a generated route is:
# shape similarity, distance gap, route smoothness, and overflow over the max distance.
#
# FR:
# Évaluation.
# Ces fonctions mesurent la qualité d’un trajet généré :
# ressemblance avec la forme, écart de distance, fluidité du trajet,
# et dépassement éventuel de la distance maximale.
# ============================================================

# EN: `route_length_m` is the real length of the path on the roads. When it is not given, we fall
# back to the length of `route_points` (which may be a simplified polyline, hence slightly shorter).
# FR: `route_length_m` est la vraie longueur du trajet sur les routes. Si elle n'est pas fournie, on
# prend la longueur de `route_points` (qui peut être une polyligne simplifiée, donc un peu plus courte).
def score_solution(route_points, target_points, desired_distance_m, max_allowed_m, route_length_m=None):
    length_target = polyline_length(target_points)

    if len(route_points) < 2:
        return {
            "shape_error": float("inf"),
            "length_route": 0.0,
            "length_target": length_target,
            "length_gap": desired_distance_m,
            "over_max": max_allowed_m,
            "turn_penalty": float("inf"),
            "combined": float("inf"),
        }

    route_rs = resample_polyline(route_points, n_samples=180)
    target_rs = resample_polyline(target_points, n_samples=180)

    shape_error = float(np.mean(np.linalg.norm(route_rs - target_rs, axis=1)))
    length_route = polyline_length(route_points) if route_length_m is None else float(route_length_m)
    length_gap = abs(length_route - desired_distance_m)
    over = max(0.0, length_route - max_allowed_m)
    turn = path_turn_penalty(route_points)
    combined = shape_error + 0.010 * length_gap + 0.080 * turn + 0.120 * over

    return {
        "shape_error": shape_error,
        "length_route": length_route,
        "length_target": length_target,
        "length_gap": length_gap,
        "over_max": over,
        "turn_penalty": turn,
        "combined": combined,
    }


# ============================================================
# EN:
# Routing helpers.
# The target shape is first sampled, then snapped to the nearest road nodes,
# and finally connected through shortest paths on the graph.
#
# FR:
# Fonctions d’aide pour le routage.
# La forme cible est d’abord échantillonnée, puis accrochée aux nœuds routiers les plus proches,
# et enfin connectée par des plus courts chemins sur le graphe.
# ============================================================

def simplify_consecutive_duplicates(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


# EN: Removes short loops from a node path. When the path comes back to a node it already visited
# after less than `max_loop_m`, the detour in between is cut. This removes the back-and-forth "comb
# teeth" created when a shape point snaps to a node in a side street (go there, come back).
# Long loops are kept: they are part of the drawing (e.g. the crossing of the infinity sign).
# Linear time: each node is pushed and popped at most once.
# FR: Supprime les boucles courtes d'un chemin de nœuds. Quand le chemin revient sur un nœud déjà visité
# après moins de `max_loop_m`, le détour entre les deux est coupé. Cela supprime les « dents de peigne »
# créées quand un point de la forme s'accroche à un nœud dans une rue latérale (on y va, on revient).
# Les grandes boucles sont gardées : elles font partie du dessin (ex. le croisement du signe infini).
# Temps linéaire : chaque nœud est ajouté et retiré au plus une fois.
def remove_short_loops(path_idx, node_array, max_loop_m):
    out, cum, last_pos = [], [], {}
    for v in path_idx:
        if out:
            dx, dy = node_array[v] - node_array[out[-1]]
            d = cum[-1] + math.hypot(dx, dy)
        else:
            d = 0.0
        p = last_pos.get(v)
        if p is not None and d - cum[p] <= max_loop_m:
            for w in out[p + 1:]:
                if last_pos.get(w, -1) > p:
                    del last_pos[w]
            del out[p + 1:]
            del cum[p + 1:]
            continue
        last_pos[v] = len(out)
        out.append(v)
        cum.append(d)
    return out


# EN: Loops shorter than this many sampling steps are considered back-and-forth noise.
# FR: Les boucles plus courtes que ce nombre de pas d'échantillonnage sont considérées comme des allers-retours parasites.
LOOP_REMOVAL_STEPS = 3.0


def route_from_target(graph, target_points, sample_count=60):
    target_rs = resample_polyline(target_points, n_samples=sample_count)

    # EN: All sampled points are snapped in one vectorized KD-tree query.
    # FR: Tous les points échantillonnés sont accrochés en une seule requête KD-tree vectorisée.
    snapped_idx, snap_dists = graph.nearest_indices(target_rs)
    snapped = simplify_consecutive_duplicates(snapped_idx.tolist())

    path_idx = []
    total_cost = 0.0
    unreachable = 0

    for a, b in zip(snapped[:-1], snapped[1:]):
        sp, cost = graph.shortest_path_idx(a, b)
        if sp is None:
            unreachable += 1
            continue
        if not path_idx:
            path_idx.extend(sp)
        else:
            path_idx.extend(sp[1:])
        total_cost += cost

    sampling_step = polyline_length(target_points) / max(sample_count - 1, 1)
    path_idx = remove_short_loops(path_idx, graph.node_array, LOOP_REMOVAL_STEPS * sampling_step)

    if path_idx:
        path_points = graph.node_array[path_idx]
        route_points = simplify_path_points(path_points, angle_tol_deg=6.0)
    else:
        path_points = route_points = np.empty((0, 2), dtype=float)

    full_path = [graph.node_ids[i] for i in path_idx]
    extra = {
        "snap_mean": float(np.mean(snap_dists)) if len(snap_dists) else float("inf"),
        "shortest_path_cost": total_cost,
        "unreachable_segments": unreachable,
        "n_route_nodes": len(full_path),
        # EN: real length of the path on the roads (the simplified polyline cuts corners).
        # FR: vraie longueur du trajet sur les routes (la polyligne simplifiée coupe les virages).
        "path_length_m": polyline_length(path_points),
    }
    return full_path, route_points, extra


# ============================================================
# EN:
# Search helpers.
# These functions generate candidate positions, sizes and angles
# for shapes or letters before evaluating them on the graph.
#
# FR:
# Fonctions d’aide pour la recherche.
# Ces fonctions génèrent des positions, tailles et angles candidats
# pour les formes ou les lettres avant leur évaluation sur le graphe.
# ============================================================

def graph_center(graph):
    return np.array([
        0.5 * (graph.bounds["xmin"] + graph.bounds["xmax"]),
        0.5 * (graph.bounds["ymin"] + graph.bounds["ymax"]),
    ], dtype=float)


# EN: Estimates the dominant direction of the road network.
# This is useful to align shapes with the general street orientation.
# FR: Estime la direction dominante du réseau routier.
# Cela permet d’aligner les formes avec l’orientation générale des rues.
def dominant_graph_angle(graph):
    # EN: Main orientation of the streets: histogram of segment directions (folded to [-90, 90]),
    # weighted by segment length, over the whole graph. Before, only the first 2000 segments in
    # file order were used, so the result depended on how OSM happened to order its data.
    # Computed once per graph and cached.
    # FR: Orientation principale des rues : histogramme des directions des segments (ramenées dans
    # [-90, 90]), pondéré par leur longueur, sur tout le graphe. Avant, seuls les 2000 premiers segments
    # dans l'ordre du fichier étaient utilisés : le résultat dépendait de l'ordre des données OSM.
    # Calculé une fois par graphe puis mis en cache.
    if graph._dominant_angle is not None:
        return graph._dominant_angle

    vec = graph.node_array[graph._arc_dst] - graph.node_array[graph._arc_src]
    length = np.hypot(vec[:, 0], vec[:, 1])
    keep = length >= 5.0
    if not np.any(keep):
        graph._dominant_angle = 0.0
        return 0.0

    angles = np.degrees(np.arctan2(vec[keep, 1], vec[keep, 0]))
    angles = np.where(angles < -90, angles + 180, angles)
    angles = np.where(angles > 90, angles - 180, angles)

    bins = np.arange(-90, 91, 10)
    hist, edges = np.histogram(angles, bins=bins, weights=length[keep])
    idx = int(np.argmax(hist))
    graph._dominant_angle = float(0.5 * (edges[idx] + edges[idx + 1]))
    return graph._dominant_angle


# EN: Builds a few size candidates around the nominal requested size.
# FR: Construit plusieurs tailles candidates autour de la taille nominale demandée.
def estimate_size_candidates(base_points, desired_distance_m, shape_name):
    base_len = max(polyline_length(base_points), 1e-9)
    base_size = desired_distance_m / max(base_len, 1e-9)

    if shape_name == "text":
        factors = [0.45, 0.60, 0.75, 0.90, 1.05]
    elif shape_name in {"heart", "star", "infinity", "circle", "square"}:
        factors = [0.65, 0.80, 0.95, 1.10]
    else:
        factors = [0.75, 0.90, 1.00, 1.10]

    return [max(80.0, base_size * f) for f in factors]


# EN: Builds one transformed candidate from a base shape:
# size + rotation + translation.
# FR: Construit un candidat transformé à partir d’une forme de base :
# taille + rotation + translation.
def make_candidate_points(base_points, center, size_m, angle_deg):
    pts = fit_points(base_points, np.array([0.0, 0.0], dtype=float), size_m)
    pts = rotate_points(pts, angle_deg)
    pts[:, 0] += center[0]
    pts[:, 1] += center[1]
    return pts


# EN:
# Generates all search candidates for a shape:
# possible centers, angles, and sizes.
# Translation mode explores a few shifted centers, while projection mode only uses the graph center.
#
# FR:
# Génère tous les candidats de recherche pour une forme :
# centres possibles, angles et tailles.
# Le mode translation explore quelques centres décalés, alors que le mode projection
# n’utilise que le centre du graphe.
# EN: Search frame: the point chosen by the user (origin of the local x/y system) and a square
# whose side equals the requested distance. Before, this frame was the bounding box of the
# downloaded graph (radius = distance / 2), i.e. the same square. Defining it explicitly means the
# candidates no longer depend on how much road network we download.
# FR: Cadre de recherche : le point choisi par l'utilisateur (origine du repère local x/y) et un carré
# de côté égal à la distance demandée. Avant, ce cadre était la boîte englobante du graphe téléchargé
# (rayon = distance / 2), c'est-à-dire le même carré. Le définir explicitement permet que les
# candidats ne dépendent plus de la quantité de réseau routier téléchargée.
def search_frame(desired_distance_m):
    return np.zeros(2, dtype=float), float(desired_distance_m)


# EN: Centers and sizes tested for a shape (angles are added separately, they need the graph).
# FR: Centres et tailles testés pour une forme (les angles sont ajoutés à part, ils dépendent du graphe).
def shape_layout(base_points, desired_distance_m, shape_name, use_translation):
    center, span = search_frame(desired_distance_m)
    step = 0.12 * span

    if shape_name == "text":
        step *= 0.95

    if use_translation:
        centers = [
            center,
            center + np.array([ step, 0.0]),
            center + np.array([-step, 0.0]),
            center + np.array([0.0,  step]),
            center + np.array([0.0, -step]),
        ]
    else:
        centers = [center]

    sizes = estimate_size_candidates(base_points, desired_distance_m, shape_name)
    return centers, sizes


# EN:
# Orientation rules.
# A heart, a star, an infinity sign or a word are only recognizable when they are roughly upright:
# before, the angle was chosen around the dominant street orientation (up to ±60°), so a heart could
# end up lying on its side. Each shape now has:
# - its rotation symmetry period (a square looks the same every 90°, a star every 72°, ...),
# - the maximum tilt from upright that keeps it readable,
# - the number of angles tested.
# When the street grid orientation falls within the allowed tilt, it is added to the tested angles
# (aligning the shape with the streets usually gives cleaner routes).
# Shapes that are readable in any orientation (square, circle) are tested over their whole period,
# starting from the street orientation.
#
# FR:
# Règles d'orientation.
# Un cœur, une étoile, le signe infini ou un mot ne sont reconnaissables que s'ils sont à peu près droits :
# avant, l'angle était choisi autour de l'orientation dominante des rues (jusqu'à ±60°), et un cœur pouvait
# se retrouver couché. Chaque forme a maintenant :
# - sa période de symétrie (un carré est identique tous les 90°, une étoile tous les 72°, ...),
# - l'inclinaison maximale par rapport à la verticale qui la garde lisible,
# - le nombre d'angles testés.
# Si l'orientation des rues tombe dans l'inclinaison permise, elle est ajoutée aux angles testés
# (aligner la forme sur les rues donne en général des tracés plus nets).
# Les formes lisibles dans n'importe quel sens (carré, cercle) sont testées sur toute leur période,
# en partant de l'orientation des rues.
ORIENTATION_RULES = {
    # forme      : (période de symétrie °, inclinaison max °, nombre d'angles)
    "square":   (90.0, 45.0, 6),
    "circle":   (360.0, 180.0, 3),
    "heart":    (360.0, 20.0, 5),
    "star":     (72.0, 20.0, 5),
    "infinity": (180.0, 20.0, 5),
    "text":     (360.0, 15.0, 5),
}


def fold_angle(angle_deg, period_deg):
    """Ramène un angle dans [-période/2, période/2[."""
    return ((angle_deg + period_deg / 2.0) % period_deg) - period_deg / 2.0


def search_angles(graph, shape_name):
    period, max_tilt, count = ORIENTATION_RULES.get(shape_name, (360.0, 20.0, 5))
    street = fold_angle(dominant_graph_angle(graph), period)

    if max_tilt >= period / 2.0:
        # toute orientation est lisible : on balaie la période en partant de l'axe des rues
        return [street + k * period / count for k in range(count)]

    angles = [float(a) for a in np.linspace(-max_tilt, max_tilt, count)]
    if abs(street) <= max_tilt and min(abs(street - a) for a in angles) > 2.0:
        angles.append(street)
    return angles


# EN: Routes one candidate (shape at a given center, size and angle) and scores it.
# FR: Construit le trajet d'un candidat (forme à un centre, une taille et un angle donnés) et l'évalue.
def evaluate_candidate(graph, base_points, center, size_m, angle_deg, desired_distance_m, max_allowed_m, sample_count):
    target = make_candidate_points(base_points, center, size_m, angle_deg)
    node_path, route_points, extra = route_from_target(graph, target, sample_count=sample_count)

    metrics = score_solution(route_points, target, desired_distance_m, max_allowed_m,
                             route_length_m=extra["path_length_m"])
    metrics.update(extra)
    metrics["length_target_request"] = float(desired_distance_m)
    # Tolérance symétrique : trop court est aussi un écart (ex. ±10 % -> entre 13,5 et 16,5 km pour 15 km).
    min_allowed_m = 2.0 * desired_distance_m - max_allowed_m
    metrics["under_min"] = max(0.0, min_allowed_m - metrics["length_route"])
    metrics["angle_deg"] = float(angle_deg)
    metrics["size_m"] = float(size_m)
    metrics["center_x"] = float(center[0])
    metrics["center_y"] = float(center[1])

    return {
        "target": target,
        "node_path": node_path,
        "route_points": route_points,
        "metrics": metrics,
    }


# EN:
# Size calibration.
# The route on real roads is always longer than the ideal drawing (streets do not follow the
# curve exactly), and by how much depends on the place. Instead of testing a few fixed sizes,
# each (center, angle) pair adjusts the size until the route length matches the requested
# distance: size <- size * desired / measured. The route length grows roughly linearly with the
# size, so 2 or 3 steps are usually enough. The size/length ratio learned on one pair is used
# as the starting point for the next one. Sizes stay within [min_size, max_size] so that the
# shape always fits in the downloaded area (see required_radius_m).
# Every evaluated size is kept: the "best compromise" choice can use them all.
#
# FR:
# Calibrage de la taille.
# Le trajet sur les vraies routes est toujours plus long que le dessin idéal (les rues ne suivent pas
# exactement la courbe), et l'écart dépend du lieu. Au lieu de tester quelques tailles fixes, chaque
# couple (centre, angle) ajuste la taille jusqu'à ce que la longueur du trajet corresponde à la distance
# demandée : taille <- taille * demandée / mesurée. La longueur grandit à peu près proportionnellement
# à la taille : 2 ou 3 étapes suffisent en général. Le rapport taille/longueur appris sur un couple sert
# de point de départ au suivant. Les tailles restent dans [min_size, max_size] pour que la forme tienne
# toujours dans la zone téléchargée (voir required_radius_m).
# Toutes les tailles évaluées sont gardées : le choix du « meilleur compromis » peut les utiliser.
CALIBRATION_MAX_STEPS = 4
CALIBRATION_TOLERANCE = 0.03   # on s'arrête à ±3 % de la distance demandée
EXPECTED_DETOUR = 1.5          # estimation initiale : trajet ≈ 1,5 × longueur du dessin


def calibrated_search(graph, base_points, centers, angles, desired_distance_m, max_allowed_m,
                      sample_count, min_size, max_size):
    nominal = desired_distance_m / max(polyline_length(base_points), 1e-9)
    size_per_meter = None
    evaluated = []

    for center in centers:
        for angle in angles:
            if size_per_meter is None:
                size = nominal / EXPECTED_DETOUR
            else:
                size = desired_distance_m * size_per_meter

            for _ in range(CALIBRATION_MAX_STEPS):
                size = float(np.clip(size, min_size, max_size))
                cand = evaluate_candidate(graph, base_points, center, size, angle,
                                          desired_distance_m, max_allowed_m, sample_count)
                evaluated.append(cand)
                length = cand["metrics"]["length_route"]
                if length <= 0:
                    break
                size_per_meter = size / length
                if abs(length - desired_distance_m) <= CALIBRATION_TOLERANCE * desired_distance_m:
                    break
                next_size = float(np.clip(size * float(np.clip(desired_distance_m / length, 0.6, 1.5)),
                                          min_size, max_size))
                if abs(next_size - size) < 1e-6:
                    break  # bloqué sur une borne : inutile d'insister
                size = next_size
    return evaluated


# EN: Picks the two proposals among the evaluated candidates:
# - "closest to distance": among the candidates within ±3 % of the requested distance, the one
#   that looks best (lowest combined score); if none is that close, simply the closest one,
# - the best overall compromise between shape, distance and smoothness.
# Candidates outside the tolerance (too long or too short) are only used if nothing else is available.
# FR: Choisit les deux propositions parmi les candidats évalués :
# - « distance la plus proche » : parmi les candidats à ±3 % de la distance demandée, celui qui
#   ressemble le plus à la forme (meilleur score combiné) ; si aucun n'est aussi proche, le plus proche,
# - le meilleur compromis global entre forme, distance et fluidité.
# Les candidats hors tolérance (trop longs ou trop courts) ne servent que si rien d'autre n'est disponible.
def pick_best(evaluated):
    feasible = [
        e for e in evaluated
        if e["metrics"]["over_max"] <= 1e-6 and e["metrics"].get("under_min", 0.0) <= 1e-6
    ]

    if feasible:
        close_enough = [
            e for e in feasible
            if e["metrics"]["length_gap"] <= CALIBRATION_TOLERANCE * (e["metrics"]["length_target_request"])
        ]
        if close_enough:
            best_close = min(close_enough, key=lambda e: (e["metrics"]["combined"], e["metrics"]["length_gap"]))
        else:
            best_close = min(
                feasible,
                key=lambda e: (
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )
        best_comp = min(
            feasible,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["length_gap"],
            ),
        )
    else:
        best_close = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["over_max"],
                e["metrics"]["length_gap"],
                e["metrics"]["shape_error"],
            ),
        )
        best_comp = min(
            evaluated,
            key=lambda e: (
                e["metrics"]["combined"],
                e["metrics"]["over_max"],
            ),
        )
    return best_close, best_comp


# EN: Runs one search method (projection or translation) with size calibration.
# FR: Lance une méthode de recherche (projection ou translation) avec calibrage de la taille.
def evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, method_name):
    max_allowed_m = desired_distance_m * (1.0 + tolerance_ratio)
    use_translation = (method_name == "translation")
    centers, sizes = shape_layout(base_points, desired_distance_m, shape_name, use_translation)
    angles = search_angles(graph, shape_name)
    sample_count = 60 if shape_name == "text" else 72

    evaluated = calibrated_search(graph, base_points, centers, angles, desired_distance_m, max_allowed_m,
                                  sample_count, min_size=80.0, max_size=max(sizes))
    best_close, best_comp = pick_best(evaluated)

    return {
        "closest_to_distance": best_close,
        "best_compromise": best_comp,
        "all_candidates_count": len(evaluated),
    }


# ============================================================
# EN:
# Text split mode in V16.
# Each letter is searched independently and receives the full requested distance.
# The letters are placed around the graph center with a spacing based on graph size.
#
# FR:
# Mode texte séparé en V16.
# Chaque lettre est cherchée indépendamment et reçoit la distance complète demandée.
# Les lettres sont placées autour du centre du graphe avec un espacement basé sur la taille du graphe.
# ============================================================

# EN: Letters to draw in split mode (unknown characters are skipped, "P" if nothing is left).
# FR: Lettres à dessiner en mode séparé (caractères inconnus ignorés, "P" s'il ne reste rien).
def split_letters(text):
    letters = [ch for ch in (text or "").upper() if ch != " " and ch in GLYPHS]
    return letters or ["P"]


# EN: Layout of each letter in split mode: base polyline, tested centers and sizes.
# `direction` is the reading direction (unit vector), `normal` is perpendicular to it.
# FR: Mise en page de chaque lettre en mode séparé : polyligne de base, centres et tailles testés.
# `direction` est le sens de lecture (vecteur unitaire), `normal` lui est perpendiculaire.
def split_letter_layout(letters, per_letter_distance_m, direction, normal):
    n = len(letters)
    center, span = search_frame(per_letter_distance_m)

    spacing = 0.18 * span
    if n > 1:
        spacing = min(spacing, 0.75 * span / (n - 1))

    offsets = [((i - 0.5 * (n - 1)) * spacing) for i in range(n)]

    layout = []
    for i, ch in enumerate(letters):
        base = single_letter_polyline(ch)
        anchor = center + direction * offsets[i]

        local_centers = [
            anchor,
            anchor + 0.18 * spacing * normal,
            anchor - 0.18 * spacing * normal,
            anchor + 0.10 * spacing * direction,
            anchor - 0.10 * spacing * direction,
            anchor + 0.12 * spacing * (direction + normal),
            anchor + 0.12 * spacing * (direction - normal),
        ]

        base_len = max(polyline_length(base), 1e-9)
        nominal_size = per_letter_distance_m / base_len

        if ch in {"I", "1"}:
            size_factors = [0.70, 0.85, 1.00, 1.15, 1.30]
        else:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]

        sizes = [max(120.0, nominal_size * f) for f in size_factors]
        layout.append((ch, base, local_centers, sizes))
    return layout


def split_text_itineraries_full_distance(graph, text, per_letter_distance_m, tolerance_ratio):
    letters = split_letters(text)
    # Lettres droites, lues de gauche à droite (voir ORIENTATION_RULES).
    angles = search_angles(graph, "text")
    direction = np.array([1.0, 0.0], dtype=float)
    normal = np.array([0.0, 1.0], dtype=float)

    results = []
    for ch, base, local_centers, sizes in split_letter_layout(letters, per_letter_distance_m, direction, normal):
        evaluated = calibrated_search(
            graph, base, local_centers, angles,
            per_letter_distance_m, per_letter_distance_m * (1.0 + tolerance_ratio),
            sample_count=64, min_size=min(sizes), max_size=max(sizes),
        )
        best, _ = pick_best(evaluated)
        best["letter"] = ch
        best["target_distance"] = per_letter_distance_m
        results.append(best)

    return results


# ============================================================
# EN:
# Extraction radius.
# The road network only has to cover the candidates that will actually be tested.
# Every candidate is "shape of size S, centered at c, rotated by some angle", so all its points
# lie within |c| + S * r_max of the origin, whatever the angle (r_max = largest distance from the
# shape's center at size 1). Taking the maximum over all candidates, plus a margin for the small
# detours of real roads, gives the radius to download.
#
# FR:
# Rayon d'extraction.
# Le réseau routier n'a besoin de couvrir que les candidats qui seront réellement testés.
# Chaque candidat est « forme de taille S, centrée en c, tournée d'un certain angle » : tous ses points
# sont donc à moins de |c| + S * r_max de l'origine, quel que soit l'angle (r_max = plus grande distance
# au centre de la forme à la taille 1). Le maximum sur tous les candidats, plus une marge pour les
# petits détours des vraies routes, donne le rayon à télécharger.
# ============================================================

def _shape_extent_m(base_points, centers, sizes):
    unit = fit_points(base_points, np.zeros(2, dtype=float), 1.0)
    r_max = float(np.max(np.hypot(unit[:, 0], unit[:, 1])))
    return max(float(np.hypot(*c)) for c in centers) + max(sizes) * r_max


def required_radius_m(drawing, distance_m):
    drawing = drawing or {}
    mode = drawing.get("mode", "shape")
    text = (drawing.get("text") or "P2I").upper()

    if mode == "text":
        base = get_base_shape("text", text)
        centers, sizes = shape_layout(base, distance_m, "text", use_translation=True)
        extent = _shape_extent_m(base, centers, sizes)
        # Lettres séparées : les distances au centre ne dépendent pas de l'orientation,
        # on peut donc prendre le sens de lecture (1, 0).
        direction, normal = np.array([1.0, 0.0]), np.array([0.0, 1.0])
        for _, letter_base, letter_centers, letter_sizes in split_letter_layout(
            split_letters(text), distance_m, direction, normal
        ):
            extent = max(extent, _shape_extent_m(letter_base, letter_centers, letter_sizes))
    else:
        shape_name = drawing.get("shape", "heart")
        base = get_base_shape(shape_name, text)
        centers, sizes = shape_layout(base, distance_m, shape_name, use_translation=True)
        extent = _shape_extent_m(base, centers, sizes)

    # Marge pour les détours ; jamais plus que l'ancien rayon (distance / 2), qui reste un plafond.
    margin = 600.0 + 0.05 * extent
    return float(min(extent + margin, distance_m / 2.0))


# ============================================================
# EN:
# Plotting helpers.
# They are mainly useful for experiments and debugging:
# visual comparison between the target shape and the generated route,
# local zoom, graph display, and metric display.
#
# FR:
# Fonctions d’affichage.
# Elles sont surtout utiles pour les expérimentations et le débogage :
# comparaison visuelle entre la forme cible et le trajet généré,
# zoom local, affichage du graphe, et affichage des métriques.
# ============================================================

def draw_graph(ax, graph, max_edges=3500):
    count = 0
    seen = set()

    for e in graph.edges:
        u = e["from"]
        v = e["to"]
        key = tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)

        pu = graph.node_xy.get(u)
        pv = graph.node_xy.get(v)
        if pu is None or pv is None:
            continue

        ax.plot([pu[0], pv[0]], [pu[1], pv[1]], linewidth=0.35, alpha=0.25)
        count += 1
        if count >= max_edges:
            break


def annotate_metrics(ax, metrics, desired_distance_m, tolerance_ratio):
    max_allowed = desired_distance_m * (1.0 + tolerance_ratio)
    txt = (
        f"route = {metrics.get('length_route', 0.0):.0f} m\n"
        f"target = {metrics.get('length_target', 0.0):.0f} m\n"
        f"gap = {metrics.get('length_gap', 0.0):.0f} m\n"
        f"max = {max_allowed:.0f} m\n"
        f"over = {metrics.get('over_max', 0.0):.0f} m\n"
        f"shape = {metrics.get('shape_error', 0.0):.1f}\n"
        f"turn = {metrics.get('turn_penalty', 0.0):.1f}\n"
        f"angle = {metrics.get('angle_deg', 0.0):.1f}°"
    )
    ax.text(0.02, 0.02, txt, transform=ax.transAxes, fontsize=8, bbox=dict(boxstyle="round", alpha=0.85))


def variant_title(method_name, variant_name):
    left = "Projection" if method_name == "projection" else "Translation"
    right = "Distance la plus proche" if variant_name == "closest_to_distance" else "Meilleur compromis"
    return f"{left} - {right}"


def set_local_view(ax, target, route):
    pts = []
    if len(target) > 0:
        pts.append(target)
    if len(route) > 0:
        pts.append(route)
    if pts:
        all_pts = np.vstack(pts)
        xmin, ymin = np.min(all_pts, axis=0)
        xmax, ymax = np.max(all_pts, axis=0)
        pad = max(xmax - xmin, ymax - ymin) * 0.6 + 100.0
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        ax.set_xlim(cx - pad, cx + pad)
        ax.set_ylim(cy - pad, cy + pad)


def plot_results(graph, results, desired_distance_m, tolerance_ratio, title):
    plt = _plt()
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.ravel()

    order = [
        ("projection", "closest_to_distance"),
        ("projection", "best_compromise"),
        ("translation", "closest_to_distance"),
        ("translation", "best_compromise"),
    ]

    for ax, (method_name, variant_name) in zip(axes, order):
        block = results[method_name][variant_name]
        target = block["target"]
        route = block["route_points"]

        draw_graph(ax, graph)

        if len(target) > 0:
            ax.plot(target[:, 0], target[:, 1], "--", linewidth=2, label="cible")
        if len(route) > 0:
            ax.plot(route[:, 0], route[:, 1], linewidth=2.2, label="trajet")

        ax.set_title(variant_title(method_name, variant_name))
        ax.set_aspect("equal")
        ax.legend()
        annotate_metrics(ax, block["metrics"], desired_distance_m, tolerance_ratio)
        set_local_view(ax, target, route)

    fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def plot_split_text_results(graph, split_results, per_letter_distance_m, tolerance_ratio, text):
    n = len(split_results)
    cols = 2 if n > 1 else 1
    rows = math.ceil(n / cols)

    plt = _plt()
    fig, axes = plt.subplots(rows, cols, figsize=(8 * cols, 5 * rows))
    axes = np.array(axes).reshape(-1)

    for ax, item in zip(axes, split_results):
        draw_graph(ax, graph)

        target = item["target"]
        route = item["route_points"]

        ax.plot(target[:, 0], target[:, 1], "--", linewidth=2, label="cible")
        if len(route) > 0:
            ax.plot(route[:, 0], route[:, 1], linewidth=2.2, label="trajet")

        ax.set_title(f"Lettre {item['letter']} - cible ~ {per_letter_distance_m:.0f} m")
        ax.set_aspect("equal")
        ax.legend()
        annotate_metrics(ax, item["metrics"], per_letter_distance_m, tolerance_ratio)
        set_local_view(ax, target, route)

    for ax in axes[len(split_results):]:
        ax.axis("off")

    fig.suptitle(f"RunToDraw V16 - texte séparé : {text.upper()} ({n} itinéraires)")
    plt.tight_layout()
    plt.show()


def plot_split_text_global(graph, split_results, text):
    plt = _plt()
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    draw_graph(ax, graph)

    first_target = True
    first_route = True

    for item in split_results:
        target = item["target"]
        route = item["route_points"]

        if len(target) > 0:
            ax.plot(
                target[:, 0],
                target[:, 1],
                "--",
                linewidth=2,
                label="cible" if first_target else None,
            )
            first_target = False

        if len(route) > 0:
            ax.plot(
                route[:, 0],
                route[:, 1],
                linewidth=2.2,
                label="trajet" if first_route else None,
            )
            first_route = False

    ax.set_title(f"RunToDraw V16 - mot global : {text.upper()}")
    ax.set_aspect("equal")
    ax.legend()

    pts = []
    for item in split_results:
        if len(item["target"]) > 0:
            pts.append(item["target"])
        if len(item["route_points"]) > 0:
            pts.append(item["route_points"])

    if pts:
        all_pts = np.vstack(pts)
        xmin, ymin = np.min(all_pts, axis=0)
        xmax, ymax = np.max(all_pts, axis=0)
        pad = max(xmax - xmin, ymax - ymin) * 0.8 + 120.0
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        ax.set_xlim(cx - pad, cx + pad)
        ax.set_ylim(cy - pad, cy + pad)

    plt.tight_layout()
    plt.show()


# ============================================================
# EN:
# Main execution helpers.
# These functions are mostly used when this file is run directly from the command line.
# They make testing easier outside of the web application.
#
# FR:
# Fonctions principales d’exécution.
# Ces fonctions sont surtout utilisées quand ce fichier est lancé directement en ligne de commande.
# Elles facilitent les tests en dehors de l’application web.
# ============================================================

def ask_distance_if_missing(distance_m):
    if distance_m is not None:
        return float(distance_m)
    while True:
        raw = input("Distance souhaitée en mètres ? ").strip()
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("Entre un nombre valide, par exemple 15000")


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


def print_summary(results):
    print("\n===== Summary =====")
    for method_name, variants in results.items():
        print(f"\n[{method_name.upper()}]")
        for variant_name in ["closest_to_distance", "best_compromise"]:
            m = variants[variant_name]["metrics"]
            print(
                f"{variant_name:20s} | route={m['length_route']:8.1f} m | "
                f"gap={m['length_gap']:7.1f} | over={m['over_max']:7.1f} | "
                f"shape={m['shape_error']:7.1f} | turn={m['turn_penalty']:7.1f} | "
                f"angle={m['angle_deg']:6.1f}"
            )


def print_split_summary(split_results):
    print("\n===== Split text summary =====")
    for i, item in enumerate(split_results, start=1):
        m = item["metrics"]
        print(
            f"{i:02d} - {item['letter']} | route={m['length_route']:8.1f} m | "
            f"target={m['length_target']:8.1f} m | "
            f"gap={m['length_gap']:7.1f} | over={m['over_max']:7.1f} | "
            f"shape={m['shape_error']:7.1f} | turn={m['turn_penalty']:7.1f} | "
            f"angle={m['angle_deg']:6.1f}"
        )


# EN:
# Main experiment function.
# It loads a graph from JSON, runs either a shape search or a text search,
# plots the results, and prints a summary.
#
# FR:
# Fonction principale d’expérimentation.
# Elle charge un graphe depuis un JSON, lance soit une recherche de forme,
# soit une recherche de texte, affiche les résultats, puis imprime un résumé.
def run_experiment(json_path, shape_name="heart", text="P2I", distance_m=None, tolerance_ratio=0.10, text_mode="whole"):
    desired_distance_m = ask_distance_if_missing(distance_m)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = RoadGraph(data)

    if shape_name == "text" and text_mode in {"split", "both"}:
        split_results = split_text_itineraries_full_distance(
            graph,
            text,
            desired_distance_m,
            tolerance_ratio,
        )
        plot_split_text_results(graph, split_results, desired_distance_m, tolerance_ratio, text)
        plot_split_text_global(graph, split_results, text)
        print_split_summary(split_results)

        if text_mode == "split":
            return split_results

    base_points = get_base_shape(shape_name, text)
    results = {
        "projection": evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, "projection"),
        "translation": evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, "translation"),
    }

    title = f"RunToDraw V16 - {shape_name}"
    if shape_name == "text":
        title += f" - {text.upper()}"

    plot_results(graph, results, desired_distance_m, tolerance_ratio, title)
    print_summary(results)
    return results


# EN: Command-line entry point.
# This makes the file usable as a standalone experiment script.
# FR: Point d’entrée en ligne de commande.
# Cela permet d’utiliser ce fichier comme script d’expérimentation autonome.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Chemin vers le JSON du graphe")
    parser.add_argument("--shape", default="heart", choices=["square", "circle", "heart", "star", "infinity", "text"])
    parser.add_argument("--text", default="P2I", help="Texte à dessiner en MAJUSCULES si --shape text")
    parser.add_argument("--distance", type=float, default=None, help="Distance souhaitée en mètres")
    parser.add_argument("--tolerance", type=float, default=0.10, help="Tolérance relative au-dessus de la distance, ex: 0.10 pour +10%%")
    parser.add_argument("--text-mode", default="split", choices=["whole", "split", "both"], help="Pour --shape text: mot complet, lettres séparées, ou les deux")
    args = parser.parse_args()

    run_experiment(
        args.json,
        shape_name=args.shape,
        text=args.text,
        distance_m=args.distance,
        tolerance_ratio=args.tolerance,
        text_mode=args.text_mode,
    )