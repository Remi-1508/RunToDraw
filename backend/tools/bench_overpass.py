"""Compare la vitesse de plusieurs requêtes Overpass pour une même zone.

Usage (depuis le dossier backend) :
    python tools/bench_overpass.py 44.80654 -0.60206 6000

Lance 3 variantes l'une après l'autre (pause entre chaque pour ne pas être limité par
Overpass) et affiche, pour chacune : durée, taille téléchargée, nombre de nœuds et de voies.
Compte environ 3 à 5 minutes au total.
"""
import math
import sys
import time

import requests

lat, lon, radius = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])

FILTERS = '["highway"]["highway"!~"motorway|motorway_link|trunk|trunk_link"]["area"!="yes"]["access"!="private"]'
dlat = radius / 111320.0
dlon = radius / (111320.0 * math.cos(math.radians(lat)))
bbox = f"{lat - dlat},{lon - dlon},{lat + dlat},{lon + dlon}"

VARIANTS = [
    ("cercle (around), actuel", "https://overpass-api.de/api/interpreter",
     f"[out:json][timeout:180];(way(around:{radius:.0f},{lat},{lon}){FILTERS};);out body;>;out skel qt;"),
    ("rectangle (bbox)", "https://overpass-api.de/api/interpreter",
     f"[out:json][timeout:180][bbox:{bbox}];(way{FILTERS};);out body;>;out skel qt;"),
    ("rectangle (bbox), miroir kumi", "https://overpass.kumi.systems/api/interpreter",
     f"[out:json][timeout:180][bbox:{bbox}];(way{FILTERS};);out body;>;out skel qt;"),
]

for i, (name, url, query) in enumerate(VARIANTS):
    if i:
        print("   (pause de 20 s)")
        time.sleep(20)
    t = time.perf_counter()
    try:
        r = requests.get(url, params={"data": query}, timeout=200, headers={"User-Agent": "RunToDraw/1.0 (bench)"})
        dt = time.perf_counter() - t
        if r.status_code != 200:
            print(f"{name:32} HTTP {r.status_code} après {dt:.1f} s : {r.text[:120]!r}")
            continue
        els = r.json().get("elements", [])
        n_nodes = sum(e["type"] == "node" for e in els)
        n_ways = sum(e["type"] == "way" for e in els)
        print(f"{name:32} {dt:6.1f} s | {len(r.content) / 1e6:5.1f} Mo | {n_nodes} nœuds, {n_ways} voies")
    except Exception as e:
        print(f"{name:32} échec après {time.perf_counter() - t:.1f} s : {e}")
