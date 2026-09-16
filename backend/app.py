from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict

from runtodraw import jobs
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
#
# Reste utile pour un appel simple (script, test), mais une planification
# complète peut prendre plusieurs dizaines de secondes : en déploiement,
# derrière un proxy avec un timeout court, préférer les deux endpoints ci-
# dessous (création d'une tâche + suivi par polling).
@app.post("/api/routes/plan")
def plan_routes(request: RoutePlanRequest):
    return plan_from_payload(request.model_dump())


# Démarre une planification en arrière-plan et renvoie tout de suite un
# identifiant de tâche, plutôt que de bloquer la requête HTTP le temps du
# calcul complet.
@app.post("/api/routes/plan/jobs")
def create_plan_job(request: RoutePlanRequest):
    job_id = jobs.create_job(request.model_dump())
    return {"job_id": job_id}


# Consulte l'état d'une tâche : status (pending/running/done/error),
# progression réelle (fraction des candidats déjà évalués), et le résultat
# une fois status="done".
@app.get("/api/routes/plan/jobs/{job_id}")
def get_plan_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tâche inconnue ou expirée")
    return {
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "error": job["error"],
    }
