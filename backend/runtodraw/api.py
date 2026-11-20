"""API FastAPI : point d'entrée HTTP de RunToDraw (lancement : uvicorn runtodraw.api:app)."""
import logging
import os
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from runtodraw.config import get_settings
from runtodraw.graph_cache import NoRoadsFoundError, cache_key, extraction_radius_m, get_road_graph
from runtodraw.planner import plan_from_graph, route_points_xy_to_latlon
from runtodraw.route_editing import EditError, edit_route, path_length_m
from runtodraw.text_routes import link_letter_routes
from runtodraw.status import overpass_status
from runtodraw.protection import ComputeSlots, RateLimiter, RateLimitExceeded, ServerBusy, client_ip
from runtodraw.custom_shape import MAX_RAW_POINTS, prepare_custom_shape
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
edit_rate_limiter = RateLimiter(limit=settings.edit_rate_limit_per_minute)
compute_slots = ComputeSlots(settings.max_concurrent_plans, settings.queue_timeout_s)


# Modèles de requête : ils définissent et valident les données acceptées par l'API.
class Drawing(BaseModel):
    mode: Literal["shape", "text", "custom"] = "shape"
    shape: Literal[SHAPES] = "heart"
    text: str = ""
    # Dessin libre (mode "custom") : points [x, y] du tracé, dans le repère d'un canvas (y vers le bas).
    # Après validation, ce champ contient la forme nettoyée (simplifiée, y vers le haut) utilisée par le moteur.
    points: Optional[List[List[float]]] = Field(default=None, max_length=MAX_RAW_POINTS)

    @model_validator(mode="after")
    def _prepare_points(self):
        # Le texte n'est exigé (et nettoyé) qu'en mode texte : une forme ou un dessin libre peuvent l'avoir vide.
        self.text = normalize_text(self.text) if self.mode == "text" else ""
        if self.mode == "custom":
            if not self.points:
                raise ValueError("Le dessin est vide : trace une forme avant de générer.")
            if any(len(point) != 2 for point in self.points):
                raise ValueError("Le dessin n'est pas lisible.")
            self.points = prepare_custom_shape(self.points)
        else:
            self.points = None   # les points n'ont de sens que pour le dessin libre
        return self


class GraphFetchRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    distance_km: float = Field(ge=0.5, le=settings.max_distance_km)
    drawing: Drawing = Drawing()


class RoutePlanRequest(GraphFetchRequest):
    tolerance_ratio: float = Field(default=0.10, ge=0.01, le=0.5)


# Édition manuelle : un segment du tracé (chemin en identifiants de nœuds OSM + positions des ancrages).
MAX_EDIT_SEGMENTS = 40          # un mot de 10 lettres reliées : 10 lettres + 9 liaisons
MAX_EDIT_PATH_NODES = 30_000    # largement au-dessus d'un tracé de 50 km


class EditSegment(BaseModel):
    label: str = Field(default="", max_length=60)
    kind: str = Field(default="", max_length=20)
    node_path: List[int] = Field(min_length=1, max_length=MAX_EDIT_PATH_NODES)
    anchors: List[int] = Field(max_length=MAX_EDIT_PATH_NODES)

    @model_validator(mode="after")
    def _check_anchors(self):
        if self.anchors != sorted(set(self.anchors)) or any(not 0 <= a < len(self.node_path) for a in self.anchors):
            raise ValueError("Points d'ancrage incohérents avec le chemin.")
        return self


class EditOperation(BaseModel):
    type: Literal["move", "insert", "delete"]
    anchor: int = Field(ge=0, le=MAX_EDIT_PATH_NODES)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _check_position(self):
        if self.type != "delete" and (self.lat is None or self.lon is None):
            raise ValueError("Une position est nécessaire pour déplacer ou insérer un point.")
        return self


class RouteEditRequest(GraphFetchRequest):
    segments: List[EditSegment] = Field(min_length=1, max_length=MAX_EDIT_SEGMENTS)
    segment_index: int = Field(ge=0, lt=MAX_EDIT_SEGMENTS)
    operation: EditOperation


# Limitation de débit : une instance par type d'endpoint (calcul lourd / édition légère).
def _limiter_dependency(limiter: RateLimiter, message: str):
    def check(request: Request) -> None:
        ip = client_ip(
            request.headers.get("x-forwarded-for"),
            request.client.host if request.client else None,
            settings.trusted_proxy_hops,
        )
        try:
            limiter.check(ip)
        except RateLimitExceeded as e:
            raise HTTPException(status_code=429, detail=message, headers={"Retry-After": str(e.retry_after_s)})
    return check


# Calcul lourd (téléchargement du graphe, génération) et édition légère : deux compteurs distincts.
limit_rate = _limiter_dependency(
    rate_limiter, "Trop de requêtes : patiente un instant avant de relancer une génération.")
limit_edit_rate = _limiter_dependency(
    edit_rate_limiter, "Trop de modifications d'un coup : patiente quelques secondes.")


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
            detail=(
                "Les serveurs publics d'OpenStreetMap (Overpass) sont indisponibles ou trop lents en ce moment. "
                "Réessaie dans une ou deux minutes."
            ),
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


# État des serveurs OpenStreetMap (Overpass) : l'interface s'en sert pour prévenir quand une génération risque
# d'être lente ou d'échouer. Résultat mis en cache quelques secondes (voir status.py).
@app.get("/api/status")
def status():
    return {"overpass": overpass_status()}


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


# Édite un point du tracé (déplacer / insérer / supprimer) et renvoie les segments recalculés.
# Sans état côté serveur : le client renvoie les segments courants, seuls les tronçons voisins du point
# modifié sont recalculés (deux plus courts chemins), donc la réponse est quasi instantanée.
@app.post("/api/routes/edit", dependencies=[Depends(limit_edit_rate)])
def edit_route_endpoint(request: RouteEditRequest):
    if request.segment_index >= len(request.segments):
        raise HTTPException(status_code=422, detail="Segment inconnu.")
    graph, _ = _load_graph(request)

    try:
        segments = [{"label": s.label, "kind": s.kind, "anchors": s.anchors,
                     "node_path": [graph._idx_of[n] for n in s.node_path]} for s in request.segments]
    except KeyError:
        raise HTTPException(status_code=422, detail="Ce tracé ne correspond plus à la carte chargée : relance la génération.")

    try:
        edited = edit_route(graph, segments, request.segment_index, request.operation.model_dump())
    except EditError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _serialize_segments(graph, edited)


# Lettres (éventuellement modifiées à la main) à relier en un seul parcours.
class LinkLettersRequest(GraphFetchRequest):
    letters: List[EditSegment] = Field(min_length=1, max_length=MAX_EDIT_SEGMENTS)


# « Lettres reliées » à partir des lettres actuelles : relance la jonction (sens de chaque lettre et plus courts
# chemins entre elles) sur les lettres telles que l'utilisateur les a modifiées. Sans cela, le parcours relié
# resterait celui calculé à la génération et ignorerait les modifications faites sur les lettres séparées.
@app.post("/api/routes/link", dependencies=[Depends(limit_edit_rate)])
def link_letters_endpoint(request: LinkLettersRequest):
    graph, _ = _load_graph(request)
    letter_results = [{"letter": s.label, "node_path": s.node_path, "anchor_idx": s.anchors} for s in request.letters]
    try:
        pieces, _ = link_letter_routes(graph, letter_results)
    except KeyError:
        raise HTTPException(status_code=422, detail="Ce tracé ne correspond plus à la carte chargée : relance la génération.")
    if not pieces:
        raise HTTPException(status_code=422, detail="Impossible de relier ces lettres : elles ne sont pas toutes accessibles entre elles.")
    segments = [{"label": p["letter"] or "liaison", "kind": p["kind"], "node_path": p["node_path"], "anchors": p["anchors"]}
                for p in pieces]
    return _serialize_segments(graph, segments)


# Segments en indices de nœuds -> réponse JSON (points GPS, distance, identifiants OSM, ancrages).
def _serialize_segments(graph, segments):
    out = []
    for seg in segments:
        path = seg["node_path"]
        out.append({
            "label": seg["label"],
            "kind": seg["kind"],
            "points": route_points_xy_to_latlon(graph, graph.node_array[path]),
            "distance_m": path_length_m(graph, path),
            "node_path": [graph.node_ids[i] for i in path],
            "anchors": seg["anchors"],
        })
    return {"segments": out, "total_distance_m": sum(s["distance_m"] for s in out)}
