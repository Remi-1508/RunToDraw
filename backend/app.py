from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import requests
import math
import time

from planner_adapter import plan_from_payload


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
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
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


# EN: This builds the Overpass query used to extract the road network around the
# user’s chosen point. The radius is based on the requested running distance.
# We also filter out roads that are not useful here, such as motorways or private roads.
# FR: Cette fonction construit la requête Overpass utilisée pour extraire le réseau routier
# autour du point choisi par l’utilisateur. Le rayon dépend de la distance demandée.
# On filtre aussi certaines routes peu utiles ici, comme les autoroutes ou les routes privées.
def build_overpass_query_circle(lat, lon, radius_meters):
    r = round(radius_meters)
    return f"""
[out:json][timeout:90];
(
  way(around:{r},{lat},{lon})["highway"]
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
        timeout=240,
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
def fetch_overpass_with_fallback(query, max_tries=6):
    last_err = None

    for attempt in range(max_tries):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            print(f"[Overpass] tentative {attempt + 1}/{max_tries} sur {endpoint}")
            return post_overpass(endpoint, query)
        except Exception as e:
            print(f"[Overpass] échec sur {endpoint}: {e}")
            last_err = e
            time.sleep(1.2 * (attempt + 1))

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


# EN: These request models define the data expected by the API.
# This makes the backend inputs clearer and safer.
# FR: Ces modèles de requête définissent les données attendues par l’API.
# Cela rend les entrées du backend plus claires et plus sûres.
class GraphFetchRequest(BaseModel):
    lat: float
    lon: float
    distance_km: float


class RoutePlanRequest(BaseModel):
    graph_payload: Dict[str, Any]
    distance_km: float
    drawing: Dict[str, Any]
    tolerance_ratio: float | None = 0.10


# EN: Simple endpoint used to quickly check that the backend is running.
# FR: Endpoint simple utilisé pour vérifier rapidement que le backend fonctionne.
@app.get("/health")
def health():
    return {"ok": True}


# EN: This endpoint fetches the road graph around the selected location.
# The chosen running distance is converted into a search radius, then the graph is built
# and sent back to the frontend in a format that the route generator can reuse.
# FR: Cet endpoint récupère le graphe routier autour de la zone choisie.
# La distance de course demandée est transformée en rayon de recherche, puis le graphe est construit
# et renvoyé au frontend dans un format réutilisable par le générateur d’itinéraires.
@app.post("/api/graph/fetch")
def fetch_graph(request: GraphFetchRequest):
    radius_km = request.distance_km / 2.0
    radius_m = radius_km * 1000.0

    query = build_overpass_query_circle(request.lat, request.lon, radius_m)
    osm = fetch_overpass_with_fallback(query)
    graph = build_graph_from_overpass(osm)

    return {
        "meta": {
            "center": [request.lat, request.lon],
            "radius_km": radius_km,
        },
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


# EN: This endpoint sends the graph and the user's drawing request to the planner.
# The actual route construction logic is not written here: it is delegated to planner_adapter,
# which keeps this file focused on API responsibilities.
# FR: Cet endpoint envoie le graphe et la demande de dessin de l’utilisateur au planificateur.
# La logique de construction des itinéraires n’est pas écrite ici : elle est déléguée à planner_adapter,
# ce qui permet à ce fichier de rester centré sur le rôle d’API.
@app.post("/api/routes/plan")
def plan_routes(request: RoutePlanRequest):
    return plan_from_payload(request.model_dump())