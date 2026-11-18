"""Tests des protections : limitation de débit, places de calcul, adresse IP du client, validation du texte."""
import threading
import time

import pytest

from runtodraw.protection import ComputeSlots, RateLimiter, RateLimitExceeded, ServerBusy, client_ip
from runtodraw.validation import normalize_text


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_rate_limiter_blocks_after_limit_then_recovers():
    clock = FakeClock()
    limiter = RateLimiter(limit=3, window_s=60, clock=clock)
    for _ in range(3):
        limiter.check("1.2.3.4")
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.check("1.2.3.4")
    assert 1 <= exc.value.retry_after_s <= 61
    clock.now += 61
    limiter.check("1.2.3.4")  # la fenêtre a glissé : de nouveau autorisé


def test_rate_limiter_is_per_client():
    limiter = RateLimiter(limit=1, window_s=60, clock=FakeClock())
    limiter.check("a")
    limiter.check("b")
    with pytest.raises(RateLimitExceeded):
        limiter.check("a")


def test_compute_slots_limit_concurrency_and_report_busy():
    slots = ComputeSlots(slots=1, timeout_s=0.05)
    with slots.acquire():
        with pytest.raises(ServerBusy):
            with slots.acquire():
                pass
    with slots.acquire():  # libéré à la sortie du bloc
        pass


def test_compute_slots_release_after_exception():
    slots = ComputeSlots(slots=1, timeout_s=0.05)
    with pytest.raises(RuntimeError):
        with slots.acquire():
            raise RuntimeError("échec du calcul")
    with slots.acquire():
        pass


def test_client_ip_reads_from_the_end_of_forwarded_for():
    # « 6.6.6.6 » est falsifiable (fourni par le client) ; le proxy de confiance a ajouté « 9.9.9.9 ».
    assert client_ip("6.6.6.6, 9.9.9.9", "10.0.0.1", trusted_hops=1) == "9.9.9.9"
    assert client_ip("9.9.9.9", "10.0.0.1", trusted_hops=1) == "9.9.9.9"
    assert client_ip(None, "10.0.0.1", trusted_hops=1) == "10.0.0.1"
    assert client_ip("6.6.6.6", "10.0.0.1", trusted_hops=0) == "10.0.0.1"
    assert client_ip(None, None) == "inconnu"


def test_normalize_text_is_permissive():
    assert normalize_text("p2i") == "P2I"
    assert normalize_text("Été  2026") == "ETE 2026"
    assert normalize_text("a-b!") == "AB"


@pytest.mark.parametrize("bad", ["", "   ", "!!!", "ABCDEFGHIJK"])
def test_normalize_text_rejects_empty_or_too_long(bad):
    with pytest.raises(ValueError):
        normalize_text(bad)
