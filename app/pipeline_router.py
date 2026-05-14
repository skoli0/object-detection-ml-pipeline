"""Web UI + JSON API to trigger downloads, validation, train, or full Prefect flow."""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.pipeline_runner import (
    run_download_web_images,
    run_prefect_flow,
    run_train,
    run_validate_data,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

ActionType = Literal["download", "validate", "train", "prefect", "refresh"]


class JobCreate(BaseModel):
    action: ActionType = Field(description="download | validate | train | prefect | refresh")
    download_count: int = Field(8, ge=1, le=64)


@lru_cache(maxsize=1)
def get_dashboard_html() -> str:
    return Path(__file__).with_name("pipeline_dashboard.html").read_text(encoding="utf-8")


def _duration_since(job_id: str) -> float:
    return round(time.time() - db.get_started_ts(job_id), 2)


def _run_job(job_id: str, action: ActionType, download_count: int) -> None:
    seed_offset = int(time.time()) % 900_001
    db.update_job(
        job_id,
        status="running",
        message="",
        error=None,
        started_ts=time.time(),
        seed_offset=seed_offset,
        download_count_requested=download_count,
    )
    try:
        if action == "download":
            run_download_web_images(download_count, seed_offset)
            db.update_job(
                job_id,
                status="completed",
                message=f"Saved {download_count} web images (seed_offset={seed_offset})",
                duration_seconds=_duration_since(job_id),
                finished_ts=time.time(),
            )
        elif action == "validate":
            run_validate_data()
            db.update_job(
                job_id,
                status="completed",
                message="Dataset validation succeeded",
                duration_seconds=_duration_since(job_id),
                finished_ts=time.time(),
                seed_offset=None,
            )
        elif action == "train":
            run_train()
            db.update_job(
                job_id,
                status="completed",
                message="Training finished",
                duration_seconds=_duration_since(job_id),
                finished_ts=time.time(),
                seed_offset=None,
            )
        elif action == "prefect":
            run_prefect_flow()
            db.update_job(
                job_id,
                status="completed",
                message="Prefect flow finished",
                duration_seconds=_duration_since(job_id),
                finished_ts=time.time(),
                seed_offset=None,
            )
        elif action == "refresh":
            run_download_web_images(download_count, seed_offset)
            run_validate_data()
            run_train()
            db.update_job(
                job_id,
                status="completed",
                message=f"Refresh: {download_count} new images, validated, trained",
                duration_seconds=_duration_since(job_id),
                finished_ts=time.time(),
            )
    except subprocess.CalledProcessError as exc:
        db.update_job(
            job_id,
            status="failed",
            error=f"exit {exc.returncode}: {exc}",
            duration_seconds=_duration_since(job_id),
            finished_ts=time.time(),
        )
    except Exception as exc:  # noqa: BLE001
        db.update_job(
            job_id,
            status="failed",
            error=str(exc),
            duration_seconds=_duration_since(job_id),
            finished_ts=time.time(),
        )


@router.post("/jobs")
def create_job(body: JobCreate, background_tasks: BackgroundTasks) -> dict:
    job_id = str(uuid.uuid4())
    db.insert_job({
        "id": job_id,
        "action": body.action,
        "status": "queued",
        "message": "",
        "error": None,
        "created_ts": time.time(),
        "download_count_requested": body.download_count,
    })
    background_tasks.add_task(_run_job, job_id, body.action, body.download_count)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return job


@router.get("/jobs")
def list_jobs() -> dict:
    return {"jobs": db.list_jobs(limit=50)}


@router.get("/config")
def pipeline_ui_config() -> dict:
    """Hints for the SPA to link out to local services (matches .env MLFLOW_PORT when set)."""
    port = os.getenv("MLFLOW_PORT", "5000")
    minio_console = os.getenv("MINIO_CONSOLE_URL")
    if not minio_console:
        minio_console_port = os.getenv("MINIO_CONSOLE_PORT", "9001")
        minio_console = f"http://127.0.0.1:{minio_console_port}/"
    return {
        "mlflow_ui": f"http://127.0.0.1:{port}/",
        "prefect_ui": "http://127.0.0.1:4200/",
        "minio_console_ui": minio_console.rstrip("/") + "/",
        "api_base": "/api/pipeline",
    }
