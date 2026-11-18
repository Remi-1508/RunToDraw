"""API FastAPI : point d'entrée HTTP de RunToDraw (lancement : uvicorn runtodraw.api:app)."""
import logging
import os
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from runtodraw.config import get_settings
from runtodraw.graph_cache import NoRoadsFoundError, cache_key, extraction_radius_m, get_road_graph
from runtodraw.planner import plan_from_graph
from runtodraw.protection import ComputeSlots, RateLimiter, RateLimitExceeded, ServerBusy, client_ip
from runtodraw.validation import SHAPES, normalize_text

# Les messages des modules RunToDraw (téléchargements Overpass, cache…) apparaissent dans les journaux de l'hébergeur.
logging.basicConfig(level=os.environ.get("RUNTODRAW_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s : %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

# Cette API sert de passerelle entre l'application React et le moteur Python de génération d'itinéraires.
app = FastAPI(title="RunToDraw Route Planner API")

# CORS : seules les origines listées (variable RUNTODRAW_ALLOWED_ORIGINS) peuvent appeler l'API depuis
# un navigateur. Aucun cookie n'est utilisé, donc pas de « credentials ».
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

rate_limiter = RateLimiter(limit=settings.rate_limit_per_minute)
compute_slots = ComputeSlots(settings.max_concurrent_plans, settings.queue_timeout_s)


# Modèles de requête : ils définissent et valident les données acceptées par l'API.
class Drawing(BaseModel):
    mode: Literal["shape", "text"] = "shape"
    shape: Literal[SHAPES] = "heart"
    text: str = "P2I"

    @field_validator("text")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        try:
            return normalize_text(value)
        except ValueError as e:
            raise ValueError(str(e))


class GraphFetchRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    distance_km: float = Field(ge=0.5, le=settings.max_distance_km)
    drawing: Drawing = Drawing()


class RoutePlanRequest(GraphFetchRequest):
    tolerance_ratio: float = Field(default=0.10, ge=0.01, le=0.5)


# Limitation de débit : appliquée aux deux endpoints coûteux (téléchargement du graphe et calcul).
def limit_rate(request: Request) -> None:
    ip = client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
        settings.trusted_proxy_hops,
    )
    try:
        rate_limiter.check(ip)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail="Trop de requêtes : patiente un instant avant de relancer une génération.",
            headers={"Retry-After": str(e.retry_after_s)},
        )


# Récupère le graphe routier en transformant les erreurs techniques en erreurs HTTP claires.
def _load_graph(request: GraphFetchRequest):
    drawing = request.drawing.model_dump()
    radius_m = extraction_radius_m(request.distance_km, drawing)
    try:
        return get_road_graph(request.lat, request.lon, radius_m), radius_m
    except NoRoadsFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Échec de la récupération du graphe routier")
        raise HTTPException(
            status_code=502,
            detail="Le service OpenStreetMap (Overpass) est indisponible ou trop lent. Réessaie dans un instant.",
        )


# Un calcul sans place disponible depuis trop longtemps : on répond « occupé » plutôt que de bloquer.
@app.exception_handler(ServerBusy)
def _server_busy(_request: Request, _exc: ServerBusy):
    return JSONResponse(
        status_code=503,
        content={"detail": "Le serveur est très sollicité. Réessaie dans quelques secondes."},
        headers={"Retry-After": "10"},
    )


# Vérifie que le backend fonctionne et expose la limite de distance, pour que le frontend la respecte.
@app.get("/health")
def health():
    return {"ok": True, "max_distance_km": settings.max_distance_km}


# Prépare le graphe routier autour du point choisi et le garde dans le cache du serveur.
# Seul un résumé est renvoyé (centre, rayon, nombre de sommets/arêtes), pas le graphe lui-même.
@app.post("/api/graph/fetch", dependencies=[Depends(limit_rate)])
def fetch_graph(request: GraphFetchRequest):
    graph, radius_m = _load_graph(request)
    return {
        "meta": {
            "center": [request.lat, request.lon],
            "radius_km": cache_key(request.lat, request.lon, radius_m)[2] / 1000.0,
            "node_count": len(graph.node_ids),
            "edge_count": graph.segment_count,
        }
    }


# Calcule les propositions d'itinéraires. Le graphe est repris dans le cache du serveur (ou retéléchargé
# s'il a expiré) ; la construction des trajets est déléguée au planificateur, un calcul à la fois par place.
@app.post("/api/routes/plan", dependencies=[Depends(limit_rate)])
def plan_routes(request: RoutePlanRequest):
    graph, _ = _load_graph(request)
    with compute_slots.acquire():
        return plan_from_graph(graph, request.distance_km, request.drawing.model_dump(), request.tolerance_ratio)
