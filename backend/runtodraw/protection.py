"""Protections de l'API contre les abus : limitation de débit par adresse IP et nombre de calculs simultanés.

Tout est en mémoire et propre à un processus : suffisant pour une instance unique (cas d'un hébergement
gratuit). Avec plusieurs instances, il faudrait un stockage partagé (Redis, par exemple).
"""
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Deque, Dict, Optional, Sequence


class RateLimitExceeded(Exception):
    """Trop de requêtes pour cette adresse ; `retry_after_s` indique quand réessayer."""

    def __init__(self, retry_after_s: int):
        super().__init__("Trop de requêtes")
        self.retry_after_s = retry_after_s


class ServerBusy(Exception):
    """Tous les emplacements de calcul sont occupés depuis trop longtemps."""


class RateLimiter:
    """Fenêtre glissante : au plus `limit` requêtes par `window_s` secondes et par clé (adresse IP)."""

    def __init__(self, limit: int, window_s: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                raise RateLimitExceeded(max(1, int(self.window_s - (now - hits[0])) + 1))
            hits.append(now)
            if len(self._hits) > 10_000:  # évite une croissance sans limite de la table
                self._purge(now)

    def _purge(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window_s]:
            del self._hits[key]


class ComputeSlots:
    """Limite le nombre de calculs menés en même temps ; les suivants patientent un temps borné."""

    def __init__(self, slots: int, timeout_s: float):
        self._semaphore = threading.BoundedSemaphore(max(1, slots))
        self._timeout_s = timeout_s

    @contextmanager
    def acquire(self):
        if not self._semaphore.acquire(timeout=self._timeout_s):
            raise ServerBusy()
        try:
            yield
        finally:
            self._semaphore.release()


def client_ip(forwarded_for: Optional[str], direct_host: Optional[str], trusted_hops: int = 1) -> str:
    """Adresse IP du client.

    Derrière `trusted_hops` proxys de confiance, chacun ajoute l'adresse qu'il a vue à la fin de
    X-Forwarded-For : on lit donc depuis la fin. Les entrées placées avant sont fournies par le client
    (falsifiables) et ne doivent pas servir de clé.
    """
    if forwarded_for and trusted_hops > 0:
        parts: Sequence[str] = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[max(0, len(parts) - trusted_hops)]
    return direct_host or "inconnu"
