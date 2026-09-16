"""File de tâches en mémoire pour les planifications longues.

Une planification (surtout en mode texte) peut prendre plusieurs dizaines de
secondes sur un vrai graphe OSM — une seule requête HTTP aussi longue risque
un timeout une fois déployée derrière un proxy ou une plateforme
d'hébergement. Ici, une tâche est créée immédiatement (job_id renvoyé tout de
suite), calculée en arrière-plan, et son état se consulte par polling — avec
une progression réelle (candidats évalués / total), pas une barre simulée
par un minuteur côté frontend.

Stockage en mémoire du processus : suffisant pour un seul serveur, perdu au
redémarrage. Passer à un stockage partagé (Redis, base de données) serait
nécessaire pour tourner à plusieurs instances derrière un load balancer.
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from . import planner

# Au-delà de cette ancienneté, une tâche terminée est purgée : évite de
# garder indéfiniment en mémoire le résultat de générations oubliées.
_JOB_TTL_SECONDS = 3600

_jobs = {}
_jobs_lock = threading.Lock()

# Deux jobs en même temps suffisent largement : chaque job utilise déjà son
# propre pool de threads pour évaluer ses candidats (voir parallel.py).
_job_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="runtodraw-job")


def _purge_expired(now):
    cutoff = now - _JOB_TTL_SECONDS
    expired = [job_id for job_id, job in _jobs.items() if job["updated_at"] < cutoff]
    for job_id in expired:
        del _jobs[job_id]


def _update(job_id, **fields):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(fields)
        job["updated_at"] = time.time()


def _run_job(job_id, payload):
    _update(job_id, status="running")

    def on_progress(fraction):
        _update(job_id, progress=fraction)

    try:
        result = planner.plan_from_payload(payload, progress_callback=on_progress)
        _update(job_id, status="done", progress=1.0, result=result)
    except Exception as exc:
        _update(job_id, status="error", error=str(exc))


def create_job(payload):
    """Crée une tâche, la lance en arrière-plan, et renvoie son identifiant tout de suite."""
    job_id = uuid.uuid4().hex
    now = time.time()
    with _jobs_lock:
        _purge_expired(now)
        _jobs[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
    _job_executor.submit(_run_job, job_id, payload)
    return job_id


def get_job(job_id):
    """État d'une tâche (status/progress/result/error), ou None si inconnue ou expirée."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None
