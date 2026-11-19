"""Réseaux routiers préchargés de grandes villes : un parcours dans une de ces zones n'attend plus Overpass.

Les serveurs Overpass publics sont gratuits mais parfois saturés ou injoignables (mesuré depuis Render : erreurs
et délais dépassés). Pour les villes les plus demandées, le réseau routier est donc téléchargé UNE fois, avec
l'outil `tools/build_city_graphs.py`, puis versionné dans `runtodraw/data/graphs/`. À la demande, on en extrait
la zone voulue (même boîte que celle qu'aurait demandée Overpass) : quelques dixièmes de seconde.

Format d'un fichier .npz (compact, comparé au JSON des nœuds et arêtes) :
- ids : identifiants OSM des nœuds ; lat, lon : coordonnées ;
- src, dst : indices (dans `ids`) des extrémités de chaque arête ; oneway : sens unique piéton.
Les longueurs sont recalculées au chargement. `index.json` liste les villes (centre, rayon couvert, fichier).
"""
import json
import logging
import math
from collections import OrderedDict
from pathlib import Path
from threading import Lock

import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data" / "graphs"
INDEX_NAME = "index.json"

_lock = Lock()
# Villes gardées en mémoire (tableaux numpy, quelques Mo chacune) : au plus MAX_LOADED, les plus anciennes sont
# libérées. La liste des villes préchargées peut donc grandir sans augmenter la mémoire du serveur.
MAX_LOADED = 3
_loaded: "OrderedDict[str, dict]" = OrderedDict()


def _read_index(data_dir):
    path = Path(data_dir) / INDEX_NAME
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("cities", [])
    except (OSError, ValueError):
        logger.warning("Index des villes préchargées illisible : %s", path)
        return []


def _distance_m(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return math.hypot(x, y) * 6371000.0


def find_city(lat, lon, radius_m, data_dir=None):
    """Ville préchargée dont la zone contient entièrement le cercle demandé, sinon None."""
    best = None
    for city in _read_index(data_dir or DATA_DIR):
        margin = city["radius_m"] - (_distance_m(lat, lon, city["lat"], city["lon"]) + radius_m)
        if margin >= 0 and (best is None or margin > best[0]):
            best = (margin, city)
    return best[1] if best else None


def _haversine_array(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000.0 * np.arcsin(np.sqrt(a))


def _load_arrays(city, data_dir):
    with _lock:
        arrays = _loaded.get(city["file"])
        if arrays is not None:
            _loaded.move_to_end(city["file"])
        else:
            with np.load(Path(data_dir) / city["file"]) as npz:
                arrays = {name: npz[name] for name in ("ids", "lat", "lon", "src", "dst", "oneway")}
            arrays["length"] = _haversine_array(
                arrays["lat"][arrays["src"]], arrays["lon"][arrays["src"]],
                arrays["lat"][arrays["dst"]], arrays["lon"][arrays["dst"]],
            )
            _loaded[city["file"]] = arrays
            while len(_loaded) > MAX_LOADED:
                _loaded.popitem(last=False)
        return arrays


def crop_city_graph(city, lat, lon, radius_m, data_dir=None):
    """Nœuds et arêtes de la boîte demandée, au même format que `build_graph_from_overpass`."""
    a = _load_arrays(city, data_dir or DATA_DIR)
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
    inside = (
        (a["lat"] >= lat - dlat) & (a["lat"] <= lat + dlat) & (a["lon"] >= lon - dlon) & (a["lon"] <= lon + dlon)
    )
    keep = inside[a["src"]] & inside[a["dst"]]
    used = np.zeros(len(a["ids"]), dtype=bool)
    used[a["src"][keep]] = True
    used[a["dst"][keep]] = True
    ids = a["ids"]
    nodes = [
        {"id": int(ids[i]), "lat": float(a["lat"][i]), "lon": float(a["lon"][i])} for i in np.flatnonzero(used)
    ]
    edges = [
        {"from": int(ids[s]), "to": int(ids[d]), "length_m": float(w), "oneway": bool(o)}
        for s, d, w, o in zip(a["src"][keep], a["dst"][keep], a["length"][keep], a["oneway"][keep])
    ]
    return {"nodes": nodes, "edges": edges}


def load_prebuilt(lat, lon, radius_m, data_dir=None):
    """Graphe brut de la zone si une ville préchargée la couvre, sinon None."""
    city = find_city(lat, lon, radius_m, data_dir)
    if city is None:
        return None
    raw = crop_city_graph(city, lat, lon, radius_m, data_dir)
    logger.info("Réseau routier préchargé (%s) : %d nœuds", city["name"], len(raw["nodes"]))
    return raw


def save_city(name, lat, lon, radius_m, raw, data_dir=None):
    """Enregistre un graphe brut (nœuds, arêtes) comme ville préchargée et met l'index à jour."""
    data_dir = Path(data_dir or DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    index_of = {n["id"]: i for i, n in enumerate(raw["nodes"])}
    edges = [e for e in raw["edges"] if e["from"] in index_of and e["to"] in index_of]
    filename = f"{name}.npz"
    np.savez_compressed(
        data_dir / filename,
        ids=np.array([n["id"] for n in raw["nodes"]], dtype=np.int64),
        lat=np.array([n["lat"] for n in raw["nodes"]], dtype=np.float64),
        lon=np.array([n["lon"] for n in raw["nodes"]], dtype=np.float64),
        src=np.array([index_of[e["from"]] for e in edges], dtype=np.int32),
        dst=np.array([index_of[e["to"]] for e in edges], dtype=np.int32),
        oneway=np.array([bool(e["oneway"]) for e in edges], dtype=bool),
    )
    cities = [c for c in _read_index(data_dir) if c["name"] != name]
    cities.append({"name": name, "lat": lat, "lon": lon, "radius_m": radius_m, "file": filename})
    (data_dir / INDEX_NAME).write_text(
        json.dumps({"cities": sorted(cities, key=lambda c: c["name"])}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with _lock:
        _loaded.pop(filename, None)
    return data_dir / filename
