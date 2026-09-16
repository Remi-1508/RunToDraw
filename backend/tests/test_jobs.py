"""Tests du magasin de tâches en mémoire (jobs.py)."""
import time

import numpy as np
import pytest

from runtodraw import jobs


def _grid_payload(n=12, spacing=80.0):
    node_xy = {i * n + j: (i * spacing, j * spacing) for i in range(n) for j in range(n)}
    nodes = []
    for nid, (x, y) in node_xy.items():
        lon = np.degrees(x / 6_371_000.0)
        lat = np.degrees(y / 6_371_000.0)
        nodes.append({"id": nid, "lat": lat, "lon": lon})

    edges = []
    for i in range(n):
        for j in range(n):
            nid = i * n + j
            if i + 1 < n:
                edges.append({"from": nid, "to": (i + 1) * n + j, "length_m": spacing})
            if j + 1 < n:
                edges.append({"from": nid, "to": i * n + (j + 1), "length_m": spacing})
    return {"meta": {"center": [0.0, 0.0]}, "nodes": nodes, "edges": edges}


def _wait_for_terminal_state(job_id, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = jobs.get_job(job_id)
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish within {timeout}s")


def test_create_job_returns_immediately_with_pending_status():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }
    t0 = time.perf_counter()
    job_id = jobs.create_job(payload)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.5  # ne doit pas attendre la fin du calcul
    job = jobs.get_job(job_id)
    assert job["status"] in ("pending", "running")
    assert job["progress"] == 0.0 or job["status"] == "running"


def test_job_progresses_to_done_with_increasing_progress_and_final_result():
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }
    job_id = jobs.create_job(payload)

    seen_progress = []
    deadline = time.time() + 15.0
    while time.time() < deadline:
        job = jobs.get_job(job_id)
        seen_progress.append(job["progress"])
        if job["status"] == "done":
            break
        time.sleep(0.02)
    else:
        raise AssertionError("job did not complete in time")

    assert seen_progress == sorted(seen_progress)
    assert job["progress"] == 1.0
    assert len(job["result"]["routes"]) == 4


def test_job_reports_error_status_for_invalid_payload():
    job_id = jobs.create_job({"graph_payload": {"nodes": []}, "distance_km": 5.0, "drawing": {}})
    job = _wait_for_terminal_state(job_id)
    assert job["status"] == "error"
    assert "invalide" in job["error"]


def test_get_job_returns_none_for_unknown_id():
    assert jobs.get_job("does-not-exist") is None


def test_expired_jobs_are_purged_on_next_create(monkeypatch):
    payload = {
        "graph_payload": _grid_payload(),
        "distance_km": 0.8,
        "drawing": {"mode": "shape", "shape": "square"},
        "tolerance_ratio": 0.10,
    }
    old_job_id = jobs.create_job(payload)
    _wait_for_terminal_state(old_job_id)

    fake_now = [time.time() + jobs._JOB_TTL_SECONDS + 1]
    monkeypatch.setattr(jobs.time, "time", lambda: fake_now[0])

    jobs.create_job(payload)  # déclenche la purge des tâches expirées
    assert jobs.get_job(old_job_id) is None
