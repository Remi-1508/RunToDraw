"""Cache des graphes routiers côté serveur : calcul du rayon à télécharger et accès au graphe."""
import logging
import math
import time
from collections import OrderedDict
from threading import Lock

from runtodraw.config import get_settings
from runtodraw.prebuilt import load_prebuilt
from runtodraw.osm import build_graph_from_overpass, build_overpass_query_bbox, fetch_overpass_with_fallback
from runtodraw.road_graph import RoadGraph
from runtodraw.search_area import required_radius_m
from runtodraw.validation import SHAPES

logger = logging.getLogger(__name__)


class NoRoadsFoundError(Exception):
    """Aucune route exploitable autour du point demandé."""


# Cache des graphes côté serveur.
# Le graphe routier reste sur le serveur : le navigateur ne le télécharge plus pour le renvoyer
# ensuite (plusieurs dizaines de Mo de JSON dans chaque sens). Un petit cache LRU garde les derniers
# graphes, indexés par (centre, rayon) : une deuxième génération dans la même zone évite Overpass.
# Seul le RoadGraph compact est conservé (les dicts JSON bruts sont libérés) pour limiter la mémoire.
GRAPH_CACHE_SIZE = get_settings().graph_cache_size
_graph_cache: "OrderedDict[tuple, RoadGraph]" = OrderedDict()
_graph_cache_lock = Lock()

# Un verrou par zone : deux demandes simultanées pour la même zone ne téléchargent qu'une fois.
_download_locks: "dict[tuple, Lock]" = {}


# Rayon à télécharger. En mode forme, on prend le plus grand rayon parmi toutes les formes :
# essayer une autre forme au même endroit et à la même distance réutilise le graphe en cache (≈ +15 % de surface).
def extraction_radius_m(distance_km, drawing):
    distance_m = distance_km * 1000.0
    if not drawing:
        return distance_m / 2.0
    if drawing.get("mode", "shape") in ("text", "custom"):
        return required_radius_m(drawing, distance_m)
    return max(required_radius_m({"mode": "shape", "shape": name}, distance_m) for name in SHAPES)


def cache_key(lat, lon, radius_m):
    # ~1 m de précision sur le centre, rayon arrondi au multiple de 50 m supérieur
    return (round(lat, 5), round(lon, 5), int(math.ceil(radius_m / 50.0) * 50))


def _cached_graph(key):
    with _graph_cache_lock:
        graph = _graph_cache.get(key)
        if graph is not None:
            _graph_cache.move_to_end(key)
        return graph


def _download_lock(key) -> Lock:
    with _graph_cache_lock:
        return _download_locks.setdefault(key, Lock())


def _build_graph(lat, lon, radius_m):
    t0 = time.perf_counter()
    # Ville préchargée : réponse immédiate, sans dépendre des serveurs Overpass publics.
    raw = load_prebuilt(lat, lon, radius_m)
    if raw is None:
        osm = fetch_overpass_with_fallback(build_overpass_query_bbox(lat, lon, radius_m))
        t1 = time.perf_counter()
        raw = build_graph_from_overpass(osm)
        del osm
    else:
        t1 = t0
    if not raw["nodes"]:
        raise NoRoadsFoundError("Aucune route trouvée autour de ce point.")
    graph = RoadGraph({"meta": {"center": [lat, lon], "radius_km": radius_m / 1000.0}, **raw})
    graph.segment_count = len(raw["edges"])
    graph.nodes = graph.edges = None  # libère les dicts JSON bruts
    del raw
    t2 = time.perf_counter()
    logger.info(
        "Graphe : %d nœuds, rayon %d m | Overpass %.1f s, construction %.1f s",
        len(graph.node_ids), radius_m, t1 - t0, t2 - t1,
    )
    return graph


def get_road_graph(lat, lon, radius_m):
    """Renvoie le graphe de la zone, depuis le cache si possible, sinon en le téléchargeant."""
    key = cache_key(lat, lon, radius_m)
    graph = _cached_graph(key)
    if graph is not None:
        logger.info("Graphe : cache %s", key)
        return graph

    with _download_lock(key):
        try:
            graph = _cached_graph(key)  # une autre requête l'a peut-être téléchargé pendant l'attente
            if graph is None:
                graph = _build_graph(lat, lon, key[2])
                with _graph_cache_lock:
                    _graph_cache[key] = graph
                    _graph_cache.move_to_end(key)
                    while len(_graph_cache) > GRAPH_CACHE_SIZE:
                        _graph_cache.popitem(last=False)
        finally:
            with _graph_cache_lock:
                _download_locks.pop(key, None)
    return graph
