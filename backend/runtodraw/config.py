"""Configuration du serveur, lue dans les variables d'environnement (voir backend/.env.example).

Les valeurs par défaut conviennent au développement local ; en production, seules
RUNTODRAW_ALLOWED_ORIGINS (et éventuellement RUNTODRAW_ALLOWED_ORIGIN_REGEX) sont à renseigner.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple


def _env_list(name: str, default: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in os.environ.get(name, default).split(",") if item.strip())


def _env_number(name: str, default: float, cast=float):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ValueError(f"Variable d'environnement {name} invalide : « {raw} » (nombre attendu).")


@dataclass(frozen=True)
class Settings:
    # Origines autorisées à appeler l'API depuis un navigateur (CORS).
    allowed_origins: Tuple[str, ...]
    # Expression régulière facultative pour autoriser aussi des adresses variables
    # (par exemple les déploiements de prévisualisation Vercel : https://runtodraw-.*\.vercel\.app).
    allowed_origin_regex: Optional[str]
    # Distance maximale d'un parcours : au-delà, la zone à télécharger devient trop grande pour Overpass.
    max_distance_km: float
    # Nombre de requêtes coûteuses (graphe, calcul) autorisées par minute et par adresse IP.
    rate_limit_per_minute: int
    # Nombre de calculs d'itinéraires menés en même temps (le calcul occupe un processeur).
    max_concurrent_plans: int
    # Temps d'attente maximal pour obtenir une place de calcul avant de répondre « serveur occupé ».
    queue_timeout_s: float
    # Nombre de graphes routiers gardés en mémoire (chacun pèse plusieurs dizaines de Mo : à réduire si la
    # mémoire de l'hébergeur est limitée, par exemple 2 sur l'offre gratuite de Render).
    graph_cache_size: int
    # Nombre de proxys de confiance devant l'API (Render : 1) pour retrouver l'adresse IP réelle.
    trusted_proxy_hops: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        allowed_origins=_env_list(
            "RUNTODRAW_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ),
        allowed_origin_regex=os.environ.get("RUNTODRAW_ALLOWED_ORIGIN_REGEX") or None,
        max_distance_km=_env_number("RUNTODRAW_MAX_DISTANCE_KM", 50.0),
        rate_limit_per_minute=_env_number("RUNTODRAW_RATE_LIMIT_PER_MINUTE", 30, int),
        max_concurrent_plans=_env_number("RUNTODRAW_MAX_CONCURRENT_PLANS", 2, int),
        queue_timeout_s=_env_number("RUNTODRAW_QUEUE_TIMEOUT_S", 60.0),
        graph_cache_size=_env_number("RUNTODRAW_GRAPH_CACHE_SIZE", 3, int),
        trusted_proxy_hops=_env_number("RUNTODRAW_TRUSTED_PROXY_HOPS", 1, int),
    )
