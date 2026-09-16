"""Graphe routier utilisé par le moteur d'itinéraires.

Construit une fois par requête à partir des nœuds/arêtes renvoyés par
Overpass, puis interrogé des dizaines de milliers de fois pendant la
recherche du meilleur itinéraire. Expose :

- `nearest_node` : le nœud du graphe le plus proche d'un point (x, y),
  via un KD-tree (scipy) plutôt qu'une comparaison à tous les nœuds ;
- `shortest_path` : le plus court chemin entre deux nœuds, par un
  Dijkstra classique avec cache (inchangé par rapport à la V16).
"""

from collections import defaultdict
from dataclasses import dataclass
import heapq

import numpy as np
from scipy.spatial import cKDTree

from . import geometry as geo


@dataclass
class EdgeData:
    to: int
    length_m: float


class RoadGraph:
    """Graphe routier en coordonnées locales x/y (mètres), centré sur meta['center']."""

    def __init__(self, data):
        self.meta = data["meta"]
        self.nodes = data["nodes"]
        self.edges = data["edges"]
        self.center_lat, self.center_lon = self.meta["center"]

        self.node_xy = {}
        for n in self.nodes:
            x, y = geo.latlon_to_xy(n["lat"], n["lon"], self.center_lat, self.center_lon)
            self.node_xy[n["id"]] = np.array([float(x), float(y)])

        self.adj = defaultdict(list)
        for e in self.edges:
            u, v = e["from"], e["to"]
            w = float(e.get("length_m", 0.0))
            self.adj[u].append(EdgeData(v, w))
            if not e.get("oneway", False):
                self.adj[v].append(EdgeData(u, w))

        self.node_ids = list(self.node_xy.keys())
        self.node_array = np.array([self.node_xy[nid] for nid in self.node_ids], dtype=float)
        self._node_from_idx = {i: nid for i, nid in enumerate(self.node_ids)}

        xs, ys = self.node_array[:, 0], self.node_array[:, 1]
        self.bounds = {
            "xmin": float(xs.min()),
            "xmax": float(xs.max()),
            "ymin": float(ys.min()),
            "ymax": float(ys.max()),
        }

        # Index spatial construit une fois : nearest_node est appelé des
        # dizaines de milliers de fois par génération, une recherche linéaire
        # dans tous les nœuds à chaque appel domine le temps de calcul.
        self._kdtree = cKDTree(self.node_array)

        self._sp_cache = {}

    def nearest_node(self, point):
        """Nœud du graphe le plus proche de point (x, y), et sa distance en mètres."""
        dist, idx = self._kdtree.query(point)
        return self._node_from_idx[int(idx)], float(dist)

    def shortest_path(self, start, goal):
        """Plus court chemin de Dijkstra entre deux nœuds, avec cache.

        Le cache est important car beaucoup de couples de nœuds sont
        redemandés plusieurs fois pendant une même recherche.
        """
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

    def path_to_points(self, node_path):
        """Convertit un chemin de nœuds en tableau de points x/y."""
        return np.array([self.node_xy[nid] for nid in node_path], dtype=float)
