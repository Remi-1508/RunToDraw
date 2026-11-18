"""Cache des graphes routiers côté serveur : calcul du rayon à télécharger et accès au graphe."""
import math
import time
from collections import OrderedDict
from threading import Lock

from runtodraw.osm import build_graph_from_overpass, build_overpass_query_bbox, fetch_overpass_with_fallback
from runtodraw.road_graph import RoadGraph
from runtodraw.search_area import required_radius_m


class NoRoadsFoundError(Exception):
    """Aucune route exploitable autour du point demandé."""


# EN:
# Server-side graph cache.
# The road graph stays on the server: the browser no longer downloads it and sends it back
# (several tens of MB of JSON each way). A small LRU cache keeps the last graphs, keyed by
# (center, radius), so a second generation in the same area skips Overpass entirely.
# Only the compact RoadGraph is kept (the raw JSON dicts are released) to limit memory use.
#
# FR:
# Cache des graphes côté serveur.
# Le graphe routier reste sur le serveur : le navigateur ne le télécharge plus pour le renvoyer
# ensuite (plusieurs dizaines de Mo de JSON dans chaque sens). Un petit cache LRU garde les derniers
# graphes, indexés par (centre, rayon) : une deuxième génération dans la même zone évite Overpass.
# Seul le RoadGraph compact est conservé (les dicts JSON bruts sont libérés) pour limiter la mémoire.
GRAPH_CACHE_SIZE = 3
_graph_cache: "OrderedDict[tuple, RoadGraph]" = OrderedDict()
_graph_cache_lock = Lock()


SHAPES = ("square", "circle", "heart", "star", "infinity")


# EN: Radius to download. In shape mode we take the largest radius over all shapes, so that
# trying another shape at the same place and distance reuses the cached graph (≈ +15 % area).
# FR: Rayon à télécharger. En mode forme, on prend le plus grand rayon parmi toutes les formes :
# essayer une autre forme au même endroit et à la même distance réutilise le graphe en cache (≈ +15 % de surface).
def extraction_radius_m(distance_km, drawing):
    distance_m = distance_km * 1000.0
    if not drawing:
        return distance_m / 2.0
    if drawing.get("mode", "shape") == "text":
        return required_radius_m(drawing, distance_m)
    return max(required_radius_m({"mode": "shape", "shape": name}, distance_m) for name in SHAPES)


def cache_key(lat, lon, radius_m):
    # ~1 m de précision sur le centre, rayon arrondi au multiple de 50 m supérieur
    return (round(lat, 5), round(lon, 5), int(math.ceil(radius_m / 50.0) * 50))


def get_road_graph(lat, lon, radius_m):
    key = cache_key(lat, lon, radius_m)
    with _graph_cache_lock:
        graph = _graph_cache.get(key)
        if graph is not None:
            _graph_cache.move_to_end(key)
            print(f"[Graphe] cache : {key}")
            return graph

    t0 = time.perf_counter()
    osm = fetch_overpass_with_fallback(build_overpass_query_bbox(lat, lon, key[2]))
    t1 = time.perf_counter()
    raw = build_graph_from_overpass(osm)
    del osm
    if not raw["nodes"]:
        raise NoRoadsFoundError("Aucune route trouvée autour de ce point.")
    graph = RoadGraph({"meta": {"center": [lat, lon], "radius_km": key[2] / 1000.0}, **raw})
    graph.segment_count = len(raw["edges"])
    graph.nodes = graph.edges = None  # libère les dicts JSON bruts
    del raw
    t2 = time.perf_counter()
    print(f"[Graphe] {len(graph.node_ids)} nœuds, rayon {key[2]} m | Overpass {t1 - t0:.1f} s, construction {t2 - t1:.1f} s")

    with _graph_cache_lock:
        _graph_cache[key] = graph
        _graph_cache.move_to_end(key)
        while len(_graph_cache) > GRAPH_CACHE_SIZE:
            _graph_cache.popitem(last=False)
    return graph
