"""Téléchargement du réseau routier depuis OpenStreetMap (Overpass) et conversion en graphe JSON."""
import logging
import math
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import requests

logger = logging.getLogger(__name__)


# Serveurs Overpass publics gratuits (https://wiki.openstreetmap.org/wiki/Overpass_API), par ordre de préférence.
# Leur rapidité varie beaucoup d'un jour à l'autre (de 10 s à plus de 2 minutes, parfois une erreur 504) :
# on ne s'appuie donc sur aucun en particulier, voir fetch_overpass_with_fallback.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",  # miroir français : bien placé pour les zones en France
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Si un serveur n'a pas répondu après ce délai, on interroge le suivant EN PARALLÈLE (sans abandonner le
# premier) : la première réponse valide l'emporte. Un serveur lent ou bloqué ne retarde plus le résultat.
HEDGE_DELAY_S = 12.0


# Cette fonction calcule la distance en mètres entre deux points GPS.
# Elle est utilisée quand on transforme les segments bruts d’OpenStreetMap en arêtes pondérées du graphe.
def haversine_meters(lat1, lon1, lat2, lon2):
    r = 6371000.0
    to_rad = math.radians
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


# Cette fonction construit la requête Overpass qui extrait le réseau routier autour du point choisi.
# On demande le carré (bbox) qui contient le cercle utile : sur Overpass, un filtre bbox est environ
# deux fois plus rapide qu'un filtre "around" (cercle), même s'il renvoie ~20 % de routes en plus
# (mesuré à Bordeaux, rayon 6 km : 46 s au lieu de 93 s).
#
# On allège aussi la réponse (mesuré à Bordeaux, rayon 7,5 km : 26 Mo en 32 s au lieu de 38 Mo en 42 s) :
# - on écarte les voies inutiles pour courir : autoroutes, routes privées ou interdites d'accès,
#   allées de parking et accès de garage, voies en projet ou en construction, voies interdites aux piétons ou
#   intérieures. Les trottoirs et passages piétons dessinés à part sont conservés : les retirer allégerait la
#   réponse, mais risquerait de supprimer des cheminements réels (par exemple le long d'une voie rapide exclue) ;
# - les étiquettes (« tags ») des voies ne sont renvoyées que pour celles à sens unique piéton
#   (« oneway:foot »), la seule information qu'on lit ensuite ; les autres voies sont envoyées « nues » (`skel`).
def build_overpass_query_bbox(lat, lon, radius_meters):
    dlat = radius_meters / 111320.0
    dlon = radius_meters / (111320.0 * math.cos(math.radians(lat)))
    return build_overpass_query(lat - dlat, lon - dlon, lat + dlat, lon + dlon)


# Même requête pour une boîte (sud, ouest, nord, est).
def build_overpass_query(south, west, north, east):
    return f"""
[out:json][timeout:180][bbox:{south:.6f},{west:.6f},{north:.6f},{east:.6f}];
way["highway"]
  ["highway"!~"motorway|motorway_link|trunk|trunk_link|proposed|construction|raceway|bus_guideway|elevator|corridor"]
  ["area"!="yes"]
  ["access"!~"private|no"]
  ["foot"!="no"]
  ["indoor"!="yes"]
  ["service"!~"parking_aisle|driveway|drive-through"]->.all;
way.all["oneway:foot"~"^(yes|1|true)$"]->.oneway;
(.all; - .oneway;)->.rest;
.oneway out body qt;
.rest out skel qt;
node(w.all);
out skel qt;
""".strip()


# Cette fonction envoie une requête à un serveur Overpass donné.
# On utilise ici une requête GET car elle s’est montrée plus stable dans nos tests qu’un POST direct.
# Si le serveur renvoie une erreur, on lève une exception avec un petit aperçu de la réponse.
def post_overpass(endpoint, query):
    res = requests.get(
        endpoint,
        params={"data": query},
        timeout=(10, 170),  # (connexion, lecture)
        headers={
            "User-Agent": "RunToDraw/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )

    if res.status_code != 200:
        preview = res.text[:300] if res.text else ""
        raise RuntimeError(f"Overpass HTTP {res.status_code} - {preview}")

    return res.json()


# Interroge les miroirs Overpass en « requêtes de secours échelonnées » :
# - le premier serveur part tout de suite ;
# - s'il échoue, on passe immédiatement au suivant ;
# - s'il est seulement lent (plus de `hedge_delay_s`), le suivant est lancé en parallèle ;
# - la première réponse valide est renvoyée, les autres sont ignorées.
# Si tous les serveurs échouent, la dernière erreur est renvoyée.
def fetch_overpass_with_fallback(query, endpoints=None, hedge_delay_s=None):
    endpoints = list(endpoints or OVERPASS_ENDPOINTS)
    hedge_delay_s = HEDGE_DELAY_S if hedge_delay_s is None else hedge_delay_s
    pool = ThreadPoolExecutor(max_workers=len(endpoints))
    running = {}
    last_err = None
    next_index = 0
    try:
        while next_index < len(endpoints) or running:
            if next_index < len(endpoints):
                endpoint = endpoints[next_index]
                logger.info("Overpass : tentative %d/%d sur %s", next_index + 1, len(endpoints), endpoint)
                running[pool.submit(post_overpass, endpoint, query)] = endpoint
                next_index += 1
            # Tant qu'il reste des serveurs à essayer, on n'attend qu'un temps limité avant d'en lancer un autre.
            timeout = hedge_delay_s if next_index < len(endpoints) else None
            done, _ = wait(list(running), timeout=timeout, return_when=FIRST_COMPLETED)
            for future in done:
                endpoint = running.pop(future)
                try:
                    result = future.result()
                except Exception as e:
                    logger.warning("Overpass : échec sur %s : %s", endpoint, e)
                    last_err = e
                    continue
                logger.info("Overpass : réponse de %s", endpoint)
                return result
        raise last_err or RuntimeError("Overpass failed")
    finally:
        # Les requêtes encore en cours se terminent d'elles-mêmes (leur résultat est simplement ignoré).
        pool.shutdown(wait=False, cancel_futures=True)


# Cette fonction transforme la réponse brute d’Overpass en un format de graphe
# attendu par le planificateur d’itinéraires. Les nœuds sont des points routiers avec latitude/longitude,
# et les arêtes sont des segments de route avec une longueur en mètres.
# Sens uniques : l'appli trace des parcours de course à pied. Le tag "oneway" ne concerne que
# les véhicules ; un piéton peut remonter une rue à sens unique. On ne garde donc un sens interdit
# que si la voie est explicitement à sens unique pour les piétons ("oneway:foot").
def build_graph_from_overpass(osm_json):
    nodes_by_id = {}
    ways = []

    for el in osm_json.get("elements", []):
        if el.get("type") == "node":
            nodes_by_id[el["id"]] = {"lat": el["lat"], "lon": el["lon"]}
        elif el.get("type") == "way":
            ways.append(el)

    edges = []

    for way in ways:
        ns = way.get("nodes")
        if not isinstance(ns, list) or len(ns) < 2:
            continue

        oneway_tag = str(way.get("tags", {}).get("oneway:foot", "")).lower()
        oneway = oneway_tag in {"yes", "1", "true"}

        for i in range(len(ns) - 1):
            a = ns[i]
            b = ns[i + 1]

            A = nodes_by_id.get(a)
            B = nodes_by_id.get(b)
            if not A or not B:
                continue

            w = haversine_meters(A["lat"], A["lon"], B["lat"], B["lon"])

            edges.append(
                {
                    "from": a,
                    "to": b,
                    "length_m": w,
                    "oneway": oneway,
                }
            )

    nodes = [
        {
            "id": nid,
            "lat": data["lat"],
            "lon": data["lon"],
        }
        for nid, data in nodes_by_id.items()
    ]

    return {
        "nodes": nodes,
        "edges": edges,
    }
