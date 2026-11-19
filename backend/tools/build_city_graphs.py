"""Télécharge le réseau routier de grandes villes pour le précharger dans l'application.

Usage (depuis le dossier backend, avec une connexion normale : à lancer chez soi, pas sur le serveur) :
    python tools/build_city_graphs.py bordeaux
    python tools/build_city_graphs.py bordeaux paris lyon
    python tools/build_city_graphs.py tokyo new-york --grid 5     # très grandes villes : morceaux plus petits
    python tools/build_city_graphs.py --list

Chaque ville est découpée en 3 x 3 morceaux (réglable avec --grid) (une seule grosse requête dépasserait le délai d'Overpass), puis
enregistrée dans runtodraw/data/graphs/<ville>.npz et ajoutée à index.json. Il suffit ensuite de versionner
ces fichiers (git add runtodraw/data) : le serveur les utilise tout seul pour les parcours situés dans la zone.
Compter 5 à 15 minutes par ville, et 2 à 6 Mo par fichier.
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtodraw.osm import build_graph_from_overpass, build_overpass_query, fetch_overpass_with_fallback  # noqa: E402
from runtodraw.prebuilt import save_city  # noqa: E402

# Nom -> (latitude, longitude, rayon couvert en mètres). Un parcours de 10 km demande ~5 km de rayon : il doit
# donc partir à moins de (rayon de la ville - 5 km) du centre pour être couvert.
CITIES = {
    # France
    "bordeaux": (44.8378, -0.5792, 12000),
    "paris": (48.8566, 2.3522, 12000),
    "lyon": (45.7640, 4.8357, 12000),
    "marseille": (43.2965, 5.3698, 12000),
    "toulouse": (43.6047, 1.4442, 12000),
    "nantes": (47.2184, -1.5536, 12000),
    "lille": (50.6292, 3.0573, 12000),
    "montpellier": (43.6108, 3.8767, 12000),
    "strasbourg": (48.5734, 7.7521, 12000),
    "nice": (43.7102, 7.2620, 12000),
    "rennes": (48.1173, -1.6778, 12000),
    "grenoble": (45.1885, 5.7245, 12000),
    "toulon": (43.1242, 5.9280, 12000),
    "dijon": (47.3220, 5.0415, 12000),
    "angers": (47.4784, -0.5632, 12000),
    "reims": (49.2583, 4.0317, 12000),
    "le-havre": (49.4944, 0.1079, 12000),
    "clermont-ferrand": (45.7772, 3.0870, 12000),
    "saint-etienne": (45.4397, 4.3872, 12000),
    "tours": (47.3941, 0.6848, 12000),
    # Europe
    "londres": (51.5074, -0.1278, 12000),
    "bruxelles": (50.8503, 4.3517, 12000),
    "amsterdam": (52.3676, 4.9041, 12000),
    "berlin": (52.5200, 13.4050, 12000),
    "madrid": (40.4168, -3.7038, 12000),
    "barcelone": (41.3874, 2.1686, 12000),
    "rome": (41.9028, 12.4964, 12000),
    "lisbonne": (38.7223, -9.1393, 12000),
    "geneve": (46.2044, 6.1432, 12000),
    "zurich": (47.3769, 8.5417, 12000),
    "vienne": (48.2082, 16.3738, 12000),
    "dublin": (53.3498, -6.2603, 12000),
    "copenhague": (55.6761, 12.5683, 12000),
    "prague": (50.0755, 14.4378, 12000),
    # Monde
    "montreal": (45.5017, -73.5673, 12000),
    "new-york": (40.7128, -74.0060, 12000),
    "tokyo": (35.6762, 139.6503, 12000),
}
DEFAULT_GRID = 3
TRIES = 3


def fetch_tile(south, west, north, east):
    for attempt in range(1, TRIES + 1):
        try:
            return build_graph_from_overpass(fetch_overpass_with_fallback(build_overpass_query(south, west, north, east)))
        except Exception as error:  # noqa: BLE001 : Overpass échoue de façons variées, on réessaie simplement
            print(f"    échec ({error.__class__.__name__}), essai {attempt}/{TRIES}")
            time.sleep(10 * attempt)
    raise SystemExit("Overpass ne répond pas : réessaie plus tard.")


def build_city(name, grid):
    lat, lon, radius_m = CITIES[name]
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
    nodes, edges = {}, {}
    t0 = time.perf_counter()
    for i in range(grid):
        for j in range(grid):
            south = lat - dlat + 2 * dlat * i / grid
            west = lon - dlon + 2 * dlon * j / grid
            print(f"  {name} : morceau {i * grid + j + 1}/{grid * grid}")
            tile = fetch_tile(south, west, south + 2 * dlat / grid, west + 2 * dlon / grid)
            for n in tile["nodes"]:
                nodes[n["id"]] = n
            for e in tile["edges"]:
                edges[(e["from"], e["to"])] = e  # les morceaux se chevauchent : on dédoublonne
    raw = {"nodes": list(nodes.values()), "edges": list(edges.values())}
    path = save_city(name, lat, lon, radius_m, raw)
    print(f"{name} : {len(raw['nodes'])} nœuds, {len(raw['edges'])} arêtes, {os.path.getsize(path) / 1e6:.1f} Mo, "
          f"{time.perf_counter() - t0:.0f} s")


if __name__ == "__main__":
    args = sys.argv[1:]
    grid = DEFAULT_GRID
    # --grid N : découpe chaque ville en N x N morceaux (4 ou 5 pour les très grandes villes, où un morceau
    # dépasse sinon le délai d'Overpass).
    if "--grid" in args:
        at = args.index("--grid")
        grid = int(args[at + 1])
        del args[at:at + 2]
    if not args or args == ["--list"]:
        print("Villes disponibles :", ", ".join(CITIES))
        sys.exit(0)
    unknown = [a for a in args if a not in CITIES]
    if unknown:
        sys.exit(f"Ville inconnue : {', '.join(unknown)}. Disponibles : {', '.join(CITIES)}")
    for city in args:
        build_city(city, grid)
