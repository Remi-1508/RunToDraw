"""API FastAPI : point d'entrée HTTP de RunToDraw (lancement : uvicorn runtodraw.api:app)."""
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from runtodraw.graph_cache import NoRoadsFoundError, cache_key, extraction_radius_m, get_road_graph
from runtodraw.planner import plan_from_graph, plan_from_payload


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


# EN: Gets the road graph, translating technical errors into clear HTTP errors.
# FR: Récupère le graphe routier en transformant les erreurs techniques en erreurs HTTP claires.
def _load_graph(lat, lon, distance_km, drawing):
    radius_m = extraction_radius_m(distance_km, drawing)
    try:
        return get_road_graph(lat, lon, radius_m), radius_m
    except NoRoadsFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenStreetMap (Overpass) indisponible : {e}")


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
    graph, radius_m = _load_graph(request.lat, request.lon, request.distance_km, request.drawing)

    return {
        "meta": {
            "center": [request.lat, request.lon],
            "radius_km": cache_key(request.lat, request.lon, radius_m)[2] / 1000.0,
            "node_count": len(graph.node_ids),
            "edge_count": graph.segment_count,
        }
    }


# EN: This endpoint computes the route proposals. The graph is taken from the server cache
# (or downloaded again if it expired); the route construction itself is delegated to planner.
# FR: Cet endpoint calcule les propositions d'itinéraires. Le graphe est repris dans le cache du serveur
# (ou retéléchargé s'il a expiré) ; la construction des trajets est déléguée à planner.
@app.post("/api/routes/plan")
def plan_routes(request: RoutePlanRequest):
    if request.graph_payload is not None:
        return plan_from_payload(request.model_dump())

    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=422, detail="lat/lon requis (ou graph_payload).")

    graph, _ = _load_graph(request.lat, request.lon, request.distance_km, request.drawing)

    return plan_from_graph(graph, request.distance_km, request.drawing, request.tolerance_ratio)
