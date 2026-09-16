from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict

from runtodraw.osm import fetch_road_graph
from runtodraw.planner import plan_from_payload


# Passerelle entre l'application React et le moteur Python de génération d'itinéraires.
app = FastAPI(title="RunToDraw Route Planner API")


# CORS activé pour que le frontend puisse appeler le backend en local pendant le développement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GraphFetchRequest(BaseModel):
    lat: float
    lon: float
    distance_km: float


class RoutePlanRequest(BaseModel):
    graph_payload: Dict[str, Any]
    distance_km: float
    drawing: Dict[str, Any]
    tolerance_ratio: float | None = 0.10


@app.get("/health")
def health():
    return {"ok": True}


# Récupère le graphe routier autour du point choisi, pour un rayon dérivé de
# la distance de course demandée.
@app.post("/api/graph/fetch")
def fetch_graph(request: GraphFetchRequest):
    return fetch_road_graph(request.lat, request.lon, request.distance_km)


# Envoie le graphe et la demande de dessin au planificateur. La logique de
# construction des itinéraires vit dans runtodraw.planner.
@app.post("/api/routes/plan")
def plan_routes(request: RoutePlanRequest):
    return plan_from_payload(request.model_dump())
