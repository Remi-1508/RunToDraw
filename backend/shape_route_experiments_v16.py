import argparse
import heapq
import json
import math
from collections import defaultdict
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np


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
    out = []
    for p in np.asarray(points, dtype=float):
        if len(out) == 0 or np.linalg.norm(p - out[-1]) > 1e-9:
            out.append(p)
    return np.asarray(out, dtype=float) if out else np.empty((0, 2), dtype=float)


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

    seg = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    total = float(seg.sum())
    if total <= 1e-12:
        return np.repeat(pts[:1], n_samples, axis=0)

    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, total, n_samples)

    out = []
    j = 0
    for t in targets:
        while j < len(seg) - 1 and cum[j + 1] < t:
            j += 1
        a = pts[j]
        b = pts[j + 1]
        denom = cum[j + 1] - cum[j]
        alpha = 0.0 if denom == 0 else (t - cum[j]) / denom
        out.append((1 - alpha) * a + alpha * b)
    return np.asarray(out, dtype=float)


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
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        a = keep[-1]
        b = pts[i]
        c = pts[i + 1]
        ab = b - a
        bc = c - b
        nab = np.linalg.norm(ab)
        nbc = np.linalg.norm(bc)
        if nab < 1e-9 or nbc < 1e-9:
            continue
        cosang = float(np.clip(np.dot(ab, bc) / (nab * nbc), -1.0, 1.0))
        ang = math.degrees(math.acos(cosang))
        if ang > angle_tol_deg:
            keep.append(b)
    keep.append(pts[-1])
    return np.asarray(keep, dtype=float)


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
    total = 0.0
    for i in range(1, len(pts) - 1):
        a = pts[i] - pts[i - 1]
        b = pts[i + 1] - pts[i]
        ang = angle_between(a, b)
        if ang > 35.0:
            total += (ang - 35.0)
    return total / max(len(pts) - 2, 1)


# EN: Small data container used in the graph adjacency list.
# FR: Petite structure de données utilisée dans la liste d’adjacence du graphe.
@dataclass
class EdgeData:
    to: int
    length_m: float


# EN:
# This class rebuilds the road graph from the exported JSON format.
# It stores:
# - the nodes in local x/y coordinates,
# - the adjacency list for shortest-path search,
# - some useful graph bounds,
# - and a cache for shortest path results.
#
# FR:
# Cette classe reconstruit le graphe routier à partir du format JSON exporté.
# Elle stocke :
# - les nœuds en coordonnées locales x/y,
# - la liste d’adjacence pour la recherche de plus court chemin,
# - quelques bornes utiles du graphe,
# - et un cache pour les résultats de plus court chemin.
class RoadGraph:
    def __init__(self, data):
        self.meta = data["meta"]
        self.nodes = data["nodes"]
        self.edges = data["edges"]
        self.center_lat, self.center_lon = self.meta["center"]

        self.node_xy = {}
        for n in self.nodes:
            x, y = latlon_to_xy_m(n["lat"], n["lon"], self.center_lat, self.center_lon)
            self.node_xy[n["id"]] = np.array([x, y], dtype=float)

        self.adj = defaultdict(list)
        for e in self.edges:
            u = e["from"]
            v = e["to"]
            w = float(e.get("length_m", 0.0))
            self.adj[u].append(EdgeData(v, w))
            if not e.get("oneway", False):
                self.adj[v].append(EdgeData(u, w))

        self.node_ids = list(self.node_xy.keys())
        self.node_array = np.array([self.node_xy[nid] for nid in self.node_ids], dtype=float)
        self._node_from_idx = {i: nid for i, nid in enumerate(self.node_ids)}

        xs = self.node_array[:, 0]
        ys = self.node_array[:, 1]
        self.bounds = {
            "xmin": float(xs.min()),
            "xmax": float(xs.max()),
            "ymin": float(ys.min()),
            "ymax": float(ys.max()),
        }
        self._sp_cache = {}

    # EN: Finds the nearest graph node to a target point.
    # This is used when we snap a theoretical shape to the road network.
    # FR: Trouve le nœud du graphe le plus proche d’un point cible.
    # C’est utilisé quand on "accroche" une forme théorique au réseau routier.
    def nearest_node(self, point):
        diffs = self.node_array - point
        d2 = np.sum(diffs * diffs, axis=1)
        idx = int(np.argmin(d2))
        return self._node_from_idx[idx], float(math.sqrt(d2[idx]))

    # EN: Standard Dijkstra shortest path between two nodes.
    # A cache is used because many node pairs are requested repeatedly during the search.
    # FR: Plus court chemin de Dijkstra classique entre deux nœuds.
    # Un cache est utilisé car beaucoup de couples de nœuds sont demandés plusieurs fois pendant la recherche.
    def shortest_path(self, start, goal):
        if start == goal:
            return [start], 0.0

        key = (start, goal)
        if key in self._sp_cache:
            return self._sp_cache[key]

        pq = [(0.0, start)]
        dist = {start: 0.0}
        prev = {}

        while pq:
            d, u = heapq.heappop(pq)
            if u == goal:
                break
            if d > dist.get(u, float("inf")):
                continue
            for e in self.adj.get(u, []):
                nd = d + e.length_m
                if nd < dist.get(e.to, float("inf")):
                    dist[e.to] = nd
                    prev[e.to] = u
                    heapq.heappush(pq, (nd, e.to))

        if goal not in dist:
            out = (None, float("inf"))
            self._sp_cache[key] = out
            return out

        path = [goal]
        cur = goal
        while cur != start:
            cur = prev[cur]
            path.append(cur)
        path.reverse()

        out = (path, dist[goal])
        self._sp_cache[key] = out
        return out

    # EN: Converts a node path into x/y points.
    # FR: Convertit un chemin de nœuds en points x/y.
    def path_to_points(self, node_path):
        return np.array([self.node_xy[nid] for nid in node_path], dtype=float)


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

def score_solution(route_points, target_points, desired_distance_m, max_allowed_m):
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
    length_route = polyline_length(route_points)
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


def route_from_target(graph, target_points, sample_count=60):
    target_rs = resample_polyline(target_points, n_samples=sample_count)

    snapped = []
    snap_dists = []
    for p in target_rs:
        nid, d = graph.nearest_node(p)
        snapped.append(nid)
        snap_dists.append(d)

    snapped = simplify_consecutive_duplicates(snapped)

    full_path = []
    total_cost = 0.0
    unreachable = 0

    for a, b in zip(snapped[:-1], snapped[1:]):
        sp, cost = graph.shortest_path(a, b)
        if sp is None:
            unreachable += 1
            continue
        if not full_path:
            full_path.extend(sp)
        else:
            full_path.extend(sp[1:])
        total_cost += cost

    if full_path:
        route_points = graph.path_to_points(full_path)
        route_points = simplify_path_points(route_points, angle_tol_deg=6.0)
    else:
        route_points = np.empty((0, 2), dtype=float)

    extra = {
        "snap_mean": float(np.mean(snap_dists)) if snap_dists else float("inf"),
        "shortest_path_cost": total_cost,
        "unreachable_segments": unreachable,
        "n_route_nodes": len(full_path),
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
def dominant_graph_angle(graph, max_edges=2000):
    angles = []
    count = 0

    for u, lst in graph.adj.items():
        pu = graph.node_xy.get(u)
        if pu is None:
            continue
        for e in lst:
            pv = graph.node_xy.get(e.to)
            if pv is None:
                continue
            v = pv - pu
            n = np.linalg.norm(v)
            if n < 5.0:
                continue
            ang = math.degrees(math.atan2(v[1], v[0]))
            while ang < -90:
                ang += 180
            while ang > 90:
                ang -= 180
            angles.append(ang)
            count += 1
            if count >= max_edges:
                break
        if count >= max_edges:
            break

    if not angles:
        return 0.0

    bins = np.arange(-90, 91, 10)
    hist, edges = np.histogram(angles, bins=bins)
    idx = int(np.argmax(hist))
    return float(0.5 * (edges[idx] + edges[idx + 1]))


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
def global_search_candidates(graph, base_points, desired_distance_m, shape_name, use_translation):
    center = graph_center(graph)
    width = graph.bounds["xmax"] - graph.bounds["xmin"]
    height = graph.bounds["ymax"] - graph.bounds["ymin"]
    step = 0.12 * min(width, height)

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

    base_angle = dominant_graph_angle(graph)

    if shape_name == "text":
        angles = [base_angle - 25, base_angle - 12, base_angle, base_angle + 12, base_angle + 25]
    else:
        angles = [base_angle + a for a in (-60, -45, -30, -15, 0, 15, 30, 45, 60)]

    sizes = estimate_size_candidates(base_points, desired_distance_m, shape_name)

    candidates = []
    for c in centers:
        for a in angles:
            for s in sizes:
                candidates.append((c.copy(), float(s), float(a)))
    return candidates


# EN:
# Evaluates all candidates for one search method and keeps the best results.
# We keep:
# - the closest candidate to the requested distance,
# - the best overall compromise between shape, distance and smoothness.
#
# FR:
# Évalue tous les candidats pour une méthode de recherche et conserve les meilleurs résultats.
# On garde :
# - le candidat le plus proche de la distance demandée,
# - le meilleur compromis global entre forme, distance et fluidité.
def evaluate_method(graph, base_points, desired_distance_m, tolerance_ratio, shape_name, method_name):
    max_allowed_m = desired_distance_m * (1.0 + tolerance_ratio)
    use_translation = (method_name == "translation")
    candidates = global_search_candidates(graph, base_points, desired_distance_m, shape_name, use_translation)

    evaluated = []
    for center, size_m, angle_deg in candidates:
        target = make_candidate_points(base_points, center, size_m, angle_deg)
        sample_count = 60 if shape_name == "text" else 72
        node_path, route_points, extra = route_from_target(graph, target, sample_count=sample_count)

        metrics = score_solution(route_points, target, desired_distance_m, max_allowed_m)
        metrics.update(extra)
        metrics["angle_deg"] = angle_deg
        metrics["size_m"] = size_m
        metrics["center_x"] = float(center[0])
        metrics["center_y"] = float(center[1])

        evaluated.append({
            "target": target,
            "node_path": node_path,
            "route_points": route_points,
            "metrics": metrics,
        })

    feasible = [e for e in evaluated if e["metrics"]["over_max"] <= 1e-6]

    if feasible:
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

def split_text_itineraries_full_distance(graph, text, per_letter_distance_m, tolerance_ratio):
    letters = [ch for ch in (text or "").upper() if ch != " " and ch in GLYPHS]
    if not letters:
        letters = ["P"]

    n = len(letters)
    center = graph_center(graph)
    dom_angle = dominant_graph_angle(graph)

    a = math.radians(dom_angle)
    direction = np.array([math.cos(a), math.sin(a)], dtype=float)
    normal = np.array([-direction[1], direction[0]], dtype=float)

    width = graph.bounds["xmax"] - graph.bounds["xmin"]
    height = graph.bounds["ymax"] - graph.bounds["ymin"]
    span = min(width, height)

    spacing = 0.18 * span
    if n > 1:
        spacing = min(spacing, 0.75 * span / (n - 1))

    offsets = [((i - 0.5 * (n - 1)) * spacing) for i in range(n)]

    results = []
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

        angles = [dom_angle - 25, dom_angle - 12, dom_angle, dom_angle + 12, dom_angle + 25]

        base_len = max(polyline_length(base), 1e-9)
        nominal_size = per_letter_distance_m / base_len

        if ch in {"I", "1"}:
            size_factors = [0.70, 0.85, 1.00, 1.15, 1.30]
        elif ch in {"M", "W"}:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]
        else:
            size_factors = [0.60, 0.75, 0.90, 1.05, 1.20]

        sizes = [max(120.0, nominal_size * f) for f in size_factors]

        evaluated = []
        for c in local_centers:
            for ang in angles:
                for size in sizes:
                    target = make_candidate_points(base, c, size, ang)
                    node_path, route_points, extra = route_from_target(graph, target, sample_count=64)

                    metrics = score_solution(
                        route_points,
                        target,
                        per_letter_distance_m,
                        per_letter_distance_m * (1.0 + tolerance_ratio),
                    )
                    metrics.update(extra)
                    metrics["angle_deg"] = ang
                    metrics["size_m"] = size

                    evaluated.append({
                        "letter": ch,
                        "target": target,
                        "route_points": route_points,
                        "node_path": node_path,
                        "metrics": metrics,
                    })

        feasible = [e for e in evaluated if e["metrics"]["over_max"] <= 1e-6]

        if feasible:
            best = min(
                feasible,
                key=lambda e: (
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )
        else:
            best = min(
                evaluated,
                key=lambda e: (
                    e["metrics"]["over_max"],
                    e["metrics"]["length_gap"],
                    e["metrics"]["shape_error"],
                    e["metrics"]["turn_penalty"],
                ),
            )

        best["target_distance"] = per_letter_distance_m
        results.append(best)

    return results


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