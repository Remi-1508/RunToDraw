from collections import OrderedDict
from threading import Lock
from typing import Any, Dict

import math
import time

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from planner_adapter import plan_from_graph, plan_from_payload
from shape_route_experiments_v16 import RoadGraph, required_radius_m


# EN: This API is the bridge between the React app and the Python route generator.
# FR: Cette API sert de passerelle entre l'application React et le moteur Python de génération d’itinéraires.
app = FastAPI(title="RunToDraw Route Planner API")


# EN: CORS is enabled so that the frontend can call the backend locally during development.
# FR: On active le CORS pour que le frontend puisse appeler le backend en local pendant le développement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# EN: Several Overpass servers are listed here because one server can be slow,
# unavailable, or reject a request. We try them one after another if needed.
# FR: On garde plusieurs serveurs Overpass ici car un serveur peut être lent,
# indisponible, ou refuser une requête. On les teste donc les uns après les autres si besoin.
# Liste issue de https://wiki.openstreetmap.org/wiki/Overpass_API (instances publiques gratuites).
# overpass-api.de est souvent saturé ; overpass.openstreetmap.ru n'est plus listé.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
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
# Pour les sens uniques, on ne garde que le sens autorisé.
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

        oneway_tag = str(way.get("tags", {}).get("oneway", "")).lower()
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


def _cache_key(lat, lon, radius_m):
    # ~1 m de précision sur le centre, rayon arrondi au multiple de 50 m supérieur
    return (round(lat, 5), round(lon, 5), int(math.ceil(radius_m / 50.0) * 50))


def get_road_graph(lat, lon, radius_m):
    key = _cache_key(lat, lon, radius_m)
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
        raise HTTPException(status_code=422, detail="Aucune route trouvée autour de ce point.")
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


# EN: These request models define the data expected by the API.
# This makes the backend inputs clearer and safer.
# FR: Ces modèles de requête définissent les données attendues par l’API.
# Cela rend les entrées du backend plus claires et plus sûres.
class GraphFetchRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    distance_km: float = Field(gt=0, le=100)
    drawing: Dict[str, Any] | None = None


class RoutePlanRequest(BaseModel):
    distance_km: float = Field(gt=0, le=100)
    drawing: Dict[str, Any]
    tolerance_ratio: float | None = 0.10
    # Nouveau fonctionnement : le serveur retrouve le graphe dans son cache à partir du point choisi.
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    # Ancien fonctionnement (toujours accepté) : le graphe complet est envoyé dans la requête.
    graph_payload: Dict[str, Any] | None = None


# EN: Simple endpoint used to quickly check that the backend is running.
# FR: Endpoint simple utilisé pour vérifier rapidement que le backend fonctionne.
@app.get("/health")
def health():
    return {"ok": True}


# EN: This endpoint prepares the road graph around the selected location and keeps it in the
# server cache. Only a summary is returned (center, radius, counts), not the graph itself.
# FR: Cet endpoint prépare le graphe routier autour du point choisi et le garde dans le cache
# du serveur. Seul un résumé est renvoyé (centre, rayon, nombre de sommets/arêtes), pas le graphe.
@app.post("/api/graph/fetch")
def fetch_graph(request: GraphFetchRequest):
    radius_m = extraction_radius_m(request.distance_km, request.drawing)
    try:
        graph = get_road_graph(request.lat, request.lon, radius_m)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenStreetMap (Overpass) indisponible : {e}")

    return {
        "meta": {
            "center": [request.lat, request.lon],
            "radius_km": _cache_key(request.lat, request.lon, radius_m)[2] / 1000.0,
            "node_count": len(graph.node_ids),
            "edge_count": graph.segment_count,
        }
    }


# EN: This endpoint computes the route proposals. The graph is taken from the server cache
# (or downloaded again if it expired); the route construction itself is delegated to planner_adapter.
# FR: Cet endpoint calcule les propositions d'itinéraires. Le graphe est repris dans le cache du serveur
# (ou retéléchargé s'il a expiré) ; la construction des trajets est déléguée à planner_adapter.
@app.post("/api/routes/plan")
def plan_routes(request: RoutePlanRequest):
    if request.graph_payload is not None:
        return plan_from_payload(request.model_dump())

    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=422, detail="lat/lon requis (ou graph_payload).")

    radius_m = extraction_radius_m(request.distance_km, request.drawing)
    try:
        graph = get_road_graph(request.lat, request.lon, radius_m)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenStreetMap (Overpass) indisponible : {e}")

    return plan_from_graph(graph, request.distance_km, request.drawing, request.tolerance_ratio)
