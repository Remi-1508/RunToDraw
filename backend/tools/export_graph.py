"""Télécharge le graphe routier d'une zone (comme l'appli) et l'enregistre en JSON compressé.

Usage (depuis le dossier backend) :
    python tools/export_graph.py 44.80654 -0.60206 15

Crée un fichier graphe_<lat>_<lon>_<km>km.json.gz, réutilisable pour les tests et les mesures
(même format que l'ancien graph_payload : meta, nodes, edges).
"""
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (  # noqa: E402
    build_graph_from_overpass,
    build_overpass_query_bbox,
    extraction_radius_m,
    fetch_overpass_with_fallback,
)

lat, lon, distance_km = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
radius_m = extraction_radius_m(distance_km, {"mode": "shape", "shape": "heart"})

t = time.perf_counter()
raw = build_graph_from_overpass(fetch_overpass_with_fallback(build_overpass_query_bbox(lat, lon, radius_m)))
print(f"{len(raw['nodes'])} nœuds, {len(raw['edges'])} arêtes, rayon {radius_m:.0f} m, {time.perf_counter() - t:.0f} s")

payload = {
    "meta": {"center": [lat, lon], "radius_km": radius_m / 1000.0},
    "nodes": [{"id": n["id"], "lat": round(n["lat"], 7), "lon": round(n["lon"], 7)} for n in raw["nodes"]],
    "edges": [{"from": e["from"], "to": e["to"], "length_m": round(e["length_m"], 2), "oneway": e["oneway"]}
              for e in raw["edges"]],
}
name = f"graphe_{lat:.5f}_{lon:.5f}_{distance_km:g}km.json.gz"
with gzip.open(name, "wt", encoding="utf-8") as f:
    json.dump(payload, f, separators=(",", ":"))
print(f"Enregistré : {os.path.abspath(name)} ({os.path.getsize(name) / 1e6:.1f} Mo)")
