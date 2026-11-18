"""RoadGraph : graphe routier compact (indices entiers, adjacence CSR, KD-tree) avec accroche des points,
plus courts chemins (A*) et accessibilité."""
import heapq
import math

from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
import numpy as np


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

        # Format CSR. Un tri stable par source conserve l'ordre d'insertion des voisins de chaque nœud,
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

        # Heuristique A* = distance à vol d'oiseau dans le plan local, multipliée par k pour qu'elle
        # ne dépasse jamais la vraie longueur d'arête (haversine). A* reste ainsi exact (même coût optimal que Dijkstra).
        if len(w):
            planar = np.hypot(xs[dst] - xs[src], ys[dst] - ys[src])
            ok = planar > 1e-9
            ratio = float(np.min(w[ok] / planar[ok])) if np.any(ok) else 1.0
            self._h_scale = max(0.0, min(1.0, ratio) * 0.999)
        else:
            self._h_scale = 0.0

        # Composantes fortement connexes + leur graphe condensé (acyclique) donnent l'accessibilité exacte.
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

        # L'accroche ne vise que la plus grande composante fortement connexe (le réseau principal).
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

    # Dictionnaire identifiant -> x/y, construit seulement si on en a besoin (tracés).
    @property
    def node_xy(self):
        if self._node_xy_dict is None:
            self._node_xy_dict = {nid: self.node_array[i] for i, nid in enumerate(self.node_ids)}
        return self._node_xy_dict

    # Trouve le nœud du réseau principal le plus proche d'un point cible (requête KD-tree).
    def nearest_node(self, point):
        d, k = self._kdtree.query(np.asarray(point, dtype=float))
        return self.node_ids[int(self._snap_idx[int(k)])], float(d)

    # Version vectorisée : tous les points d'une forme en un seul appel. Renvoie des indices de nœuds.
    def nearest_indices(self, points):
        d, k = self._kdtree.query(np.asarray(points, dtype=float))
        return self._snap_idx[np.asarray(k, dtype=np.int64)], np.asarray(d, dtype=float)

    # Vrai si `goal` est accessible depuis `start` (un parcours par composante source, mis en cache).
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

    # Plus court chemin A* exact entre deux indices de nœuds. Renvoie (chemin d'indices, coût).
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

    # Comme avant : plus court chemin entre deux identifiants de nœuds OSM.
    def shortest_path(self, start, goal):
        path, cost = self.shortest_path_idx(self._idx_of[start], self._idx_of[goal])
        if path is None:
            return None, cost
        return [self.node_ids[i] for i in path], cost

    # Convertit un chemin de nœuds (identifiants OSM) en points x/y.
    def path_to_points(self, node_path):
        return self.node_array[[self._idx_of[nid] for nid in node_path]]


def graph_center(graph):
    return np.array([
        0.5 * (graph.bounds["xmin"] + graph.bounds["xmax"]),
        0.5 * (graph.bounds["ymin"] + graph.bounds["ymax"]),
    ], dtype=float)


# Estime la direction dominante du réseau routier.
# Cela permet d’aligner les formes avec l’orientation générale des rues.
def dominant_graph_angle(graph):
    # Orientation principale des rues : histogramme des directions des segments (ramenées dans
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
