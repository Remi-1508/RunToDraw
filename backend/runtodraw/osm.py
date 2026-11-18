"""Téléchargement du réseau routier depuis OpenStreetMap (Overpass) et conversion en graphe JSON."""
import math
import time

import requests


# EN: Several Overpass servers are listed here because one server can be slow,
# unavailable, or reject a request. We try them one after another if needed.
# FR: On garde plusieurs serveurs Overpass ici car un serveur peut être lent,
# indisponible, ou refuser une requête. On les teste donc les uns après les autres si besoin.
# Liste issue de https://wiki.openstreetmap.org/wiki/Overpass_API (instances publiques gratuites).
# overpass-api.de est souvent saturé ; overpass.openstreetmap.ru n'est plus listé.
# private.coffee en premier : 10 s mesurées à Bordeaux contre ~45 s pour overpass-api.de.
OVERPASS_ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


# EN: This function computes the distance in meters between two GPS points.
# It is used when converting raw OpenStreetMap road segments into weighted graph edges.
# FR: Cette fonction calcule la distance en mètres entre deux points GPS.
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


# EN: This builds the Overpass query used to extract the road network around the user's point.
# We ask for the square (bounding box) that contains the useful circle: on Overpass, a bbox filter
# is about twice as fast as an "around" (circle) filter, even though it returns ~20 % more roads
# (measured in Bordeaux, 6 km radius: 46 s instead of 93 s).
# We also filter out roads that are not useful here, such as motorways or private roads.
# FR: Cette fonction construit la requête Overpass qui extrait le réseau routier autour du point choisi.
# On demande le carré (bbox) qui contient le cercle utile : sur Overpass, un filtre bbox est environ
# deux fois plus rapide qu'un filtre "around" (cercle), même s'il renvoie ~20 % de routes en plus
# (mesuré à Bordeaux, rayon 6 km : 46 s au lieu de 93 s).
# On filtre aussi certaines routes peu utiles ici, comme les autoroutes ou les routes privées.
def build_overpass_query_bbox(lat, lon, radius_meters):
    dlat = radius_meters / 111320.0
    dlon = radius_meters / (111320.0 * math.cos(math.radians(lat)))
    south, west, north, east = lat - dlat, lon - dlon, lat + dlat, lon + dlon
    return f"""
[out:json][timeout:180][bbox:{south:.6f},{west:.6f},{north:.6f},{east:.6f}];
(
  way["highway"]
    ["highway"!~"motorway|motorway_link|trunk|trunk_link"]
    ["area"!="yes"]
    ["access"!="private"];
);
out body;
>;
out skel qt;
""".strip()


# EN: This sends one request to one Overpass endpoint.
# We use a GET request here because it was more stable in our tests than a direct POST.
# If the server answers with an error, we raise an exception with a short preview.
# FR: Cette fonction envoie une requête à un serveur Overpass donné.
# On utilise ici une requête GET car elle s’est montrée plus stable dans nos tests qu’un POST direct.
# Si le serveur renvoie une erreur, on lève une exception avec un petit aperçu de la réponse.
def post_overpass(endpoint, query):
    res = requests.get(
        endpoint,
        params={"data": query},
        timeout=200,
        headers={
            "User-Agent": "RunToDraw/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )

    if res.status_code != 200:
        preview = res.text[:300] if res.text else ""
        raise RuntimeError(f"Overpass HTTP {res.status_code} - {preview}")

    return res.json()


# EN: This helper retries the Overpass request on several mirrors.
# It makes the extraction step more robust, because Overpass servers can be unstable.
# We keep the last error to report something meaningful if all attempts fail.
# FR: Cette fonction réessaie la requête Overpass sur plusieurs miroirs.
# Cela rend l’extraction plus robuste, car les serveurs Overpass peuvent être instables.
# On conserve la dernière erreur pour renvoyer un message utile si toutes les tentatives échouent.
def fetch_overpass_with_fallback(query, max_tries=len(OVERPASS_ENDPOINTS)):
    last_err = None

    for attempt in range(max_tries):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            print(f"[Overpass] tentative {attempt + 1}/{max_tries} sur {endpoint}")
            return post_overpass(endpoint, query)
        except Exception as e:
            print(f"[Overpass] échec sur {endpoint}: {e}")
            last_err = e
            time.sleep(2.0)

    raise last_err or RuntimeError("Overpass failed")


# EN: This converts the raw Overpass response into the graph format expected by the route planner.
# Nodes are road points with latitude/longitude, and edges are road segments with a length in meters.
# For one-way streets, we only keep the allowed direction.
# FR: Cette fonction transforme la réponse brute d’Overpass en un format de graphe
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
