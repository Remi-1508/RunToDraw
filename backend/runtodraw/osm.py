"""Extraction du réseau routier depuis Overpass (OpenStreetMap).

Convertit une position et une distance de course en requête Overpass,
récupère les données brutes (avec repli sur plusieurs serveurs miroirs), puis
les transforme dans le format `{nodes, edges}` attendu par `graph.RoadGraph`.
"""

import time

import requests

from . import geometry as geo

# Plusieurs serveurs Overpass sont listés ici car un serveur peut être lent,
# indisponible, ou refuser une requête : on les essaie l'un après l'autre.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


def build_overpass_query_circle(lat, lon, radius_meters):
    """Requête Overpass : routes praticables à pied dans un rayon donné.

    Exclut les autoroutes et les voies privées, qui ne conviennent pas pour
    un parcours de course à pied.
    """
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


def post_overpass(endpoint, query):
    """Envoie une requête à un serveur Overpass donné.

    Un GET est utilisé ici : plus stable qu'un POST direct dans nos tests.
    """
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


def fetch_overpass_with_fallback(query, max_tries=6):
    """Réessaie la requête Overpass sur plusieurs miroirs avant d'abandonner."""
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


def build_graph_from_overpass(osm_json):
    """Convertit la réponse Overpass brute en graphe {nodes, edges} pour RoadGraph.

    Pour les sens uniques, seul le sens autorisé est conservé.
    """
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

            w = geo.haversine_m(A["lat"], A["lon"], B["lat"], B["lon"])

            edges.append({
                "from": a,
                "to": b,
                "length_m": w,
                "oneway": oneway,
            })

    nodes = [
        {"id": nid, "lat": data["lat"], "lon": data["lon"]}
        for nid, data in nodes_by_id.items()
    ]

    return {"nodes": nodes, "edges": edges}


def fetch_road_graph(lat, lon, distance_km):
    """Récupère et construit le graphe routier autour d'un point pour une distance de course donnée."""
    radius_km = distance_km / 2.0
    radius_m = radius_km * 1000.0

    query = build_overpass_query_circle(lat, lon, radius_m)
    osm_json = fetch_overpass_with_fallback(query)
    graph = build_graph_from_overpass(osm_json)

    return {
        "meta": {"center": [lat, lon], "radius_km": radius_km},
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }
