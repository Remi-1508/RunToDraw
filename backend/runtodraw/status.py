"""État des serveurs Overpass (OpenStreetMap) : de quoi expliquer une génération lente ou en échec.

Chaque miroir est interrogé en parallèle sur sa page d'état, avec un délai court. Le résultat est gardé
quelques dizaines de secondes : un visiteur qui actualise la page ne déclenche donc pas de nouvelles
requêtes vers des serveurs publics qui n'ont rien demandé.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlparse

import requests

from runtodraw.osm import OVERPASS_ENDPOINTS

CHECK_TIMEOUT_S = 4.0
CACHE_TTL_S = 45.0
SLOW_MS = 2000  # au-delà, un miroir répond mais il sera lent pour télécharger un réseau routier

_lock = Lock()
_cache = {"at": 0.0, "value": None}


def _check(endpoint):
    status_url = endpoint.rsplit("/", 1)[0] + "/status"
    started = time.perf_counter()
    try:
        response = requests.get(status_url, timeout=CHECK_TIMEOUT_S, headers={"User-Agent": "RunToDraw/1.0"})
        ok = response.status_code == 200
    except requests.RequestException:
        ok = False
    return {
        "name": urlparse(endpoint).netloc,
        "ok": ok,
        "ms": round((time.perf_counter() - started) * 1000) if ok else None,
    }


def summarize(mirrors):
    """'ok' (un miroir rapide répond), 'slow' (ils répondent, mais lentement) ou 'down' (aucun ne répond)."""
    answering = [m for m in mirrors if m["ok"]]
    if not answering:
        state = "down"
    elif min(m["ms"] for m in answering) > SLOW_MS:
        state = "slow"
    else:
        state = "ok"
    return {"state": state, "available": len(answering), "total": len(mirrors), "mirrors": mirrors}


def overpass_status(endpoints=None, check=_check, now=time.monotonic):
    """État des serveurs Overpass, avec un cache de CACHE_TTL_S secondes."""
    endpoints = list(endpoints or OVERPASS_ENDPOINTS)
    with _lock:
        if _cache["value"] is not None and now() - _cache["at"] < CACHE_TTL_S:
            return _cache["value"]
    with ThreadPoolExecutor(max_workers=len(endpoints)) as pool:
        mirrors = list(pool.map(check, endpoints))
    value = summarize(mirrors)
    with _lock:
        _cache["value"], _cache["at"] = value, now()
    return value
