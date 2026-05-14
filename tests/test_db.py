"""Tests for pipeline job persistence against PostgreSQL (app/db.py)."""

from __future__ import annotations

import os
import time
import uuid

import pytest

from app import db


def _postgres_dsn_for_tests() -> str:
    return os.environ.get("DATABASE_URL") or (
        "postgresql://mlops:mlops@127.0.0.1:5432/mlflow"
    )


@pytest.fixture(autouse=True)
def postgres_jobs_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _postgres_dsn_for_tests())
    try:
        db.init_db()
        db.clear_all_jobs_for_tests()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not reachable ({_postgres_dsn_for_tests()}): {exc}")


def _new_job(action: str = "validate") -> dict:
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "action": action,
        "status": "queued",
        "message": "",
        "error": None,
        "created_ts": time.time(),
        "download_count_requested": 8,
    }
    db.insert_job(job)
    return job


def test_insert_and_get_job() -> None:
    job = _new_job("train")
    fetched = db.get_job(job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]
    assert fetched["action"] == "train"
    assert fetched["status"] == "queued"


def test_get_missing_job_returns_none() -> None:
    assert db.get_job("does-not-exist") is None


def test_update_job_status() -> None:
    job = _new_job()
    db.update_job(job["id"], status="running", started_ts=time.time())
    updated = db.get_job(job["id"])
    assert updated["status"] == "running"
    assert updated["started_ts"] is not None


def test_update_job_completed() -> None:
    job = _new_job("download")
    db.update_job(
        job["id"],
        status="completed",
        message="Saved 8 images",
        duration_seconds=3.14,
        finished_ts=time.time(),
        seed_offset=42,
    )
    result = db.get_job(job["id"])
    assert result["status"] == "completed"
    assert result["message"] == "Saved 8 images"
    assert abs(result["duration_seconds"] - 3.14) < 0.01
    assert result["seed_offset"] == 42


def test_update_job_failed() -> None:
    job = _new_job("train")
    db.update_job(job["id"], status="failed", error="Something went wrong")
    result = db.get_job(job["id"])
    assert result["status"] == "failed"
    assert "Something went wrong" in result["error"]


def test_list_jobs_ordered_newest_first() -> None:
    ids = []
    for _ in range(5):
        j = _new_job()
        ids.append(j["id"])
        time.sleep(0.01)

    jobs = db.list_jobs()
    listed_ids = [j["id"] for j in jobs]
    assert listed_ids[0] == ids[-1]
    assert listed_ids[-1] == ids[0]


def test_list_jobs_respects_limit() -> None:
    for _ in range(10):
        _new_job()
    assert len(db.list_jobs(limit=3)) == 3


def test_list_jobs_empty_after_clean() -> None:
    assert db.list_jobs() == []


def test_get_started_ts_returns_started_ts() -> None:
    job = _new_job()
    ts = time.time()
    db.update_job(job["id"], started_ts=ts)
    assert abs(db.get_started_ts(job["id"]) - ts) < 0.01


def test_get_started_ts_falls_back_to_now_for_unknown_job() -> None:
    before = time.time()
    result = db.get_started_ts("nonexistent")
    after = time.time()
    assert before <= result <= after


def test_api_create_and_list_jobs() -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        r = client.post("/api/pipeline/jobs", json={"action": "validate", "download_count": 4})
        assert r.status_code == 200
        body = r.json()
        assert "job_id" in body
        job_id = body["job_id"]

        r2 = client.get(f"/api/pipeline/jobs/{job_id}")
        assert r2.status_code == 200
        job = r2.json()
        assert job["id"] == job_id
        assert job["action"] == "validate"

        r3 = client.get("/api/pipeline/jobs")
        assert r3.status_code == 200
        ids = [j["id"] for j in r3.json()["jobs"]]
        assert job_id in ids


def test_api_get_unknown_job_404() -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        r = client.get("/api/pipeline/jobs/no-such-id")
        assert r.status_code == 404
