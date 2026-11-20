"""État des serveurs Overpass : synthèse et cache."""
from runtodraw import status


def test_summarize_states():
    ok = {"name": "a", "ok": True, "ms": 300}
    slow = {"name": "b", "ok": True, "ms": 3500}
    down = {"name": "c", "ok": False, "ms": None}
    assert status.summarize([ok, down])["state"] == "ok"
    assert status.summarize([slow, down])["state"] == "slow"
    assert status.summarize([down, down])["state"] == "down"
    assert status.summarize([ok, slow, down])["available"] == 2


def test_overpass_status_is_cached(monkeypatch):
    monkeypatch.setitem(status._cache, "value", None)
    calls = []

    def fake_check(endpoint):
        calls.append(endpoint)
        return {"name": endpoint, "ok": True, "ms": 100}

    clock = [1000.0]
    first = status.overpass_status(["https://a/api/interpreter", "https://b/api/interpreter"], fake_check, lambda: clock[0])
    clock[0] += 10  # moins que la durée du cache
    second = status.overpass_status(["https://a/api/interpreter", "https://b/api/interpreter"], fake_check, lambda: clock[0])
    assert first == second and len(calls) == 2
    clock[0] += status.CACHE_TTL_S + 1
    status.overpass_status(["https://a/api/interpreter", "https://b/api/interpreter"], fake_check, lambda: clock[0])
    assert len(calls) == 4
