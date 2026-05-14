"""PostgreSQL persistence layer for pipeline console jobs.

Uses the Postgres service from podman-compose (same database as MLflow by default).

Connection:
  DATABASE_URL                           e.g. postgresql://mlops:mlops@127.0.0.1:5432/mlflow
  — or assemble from —
  POSTGRES_USER (default mlops)
  POSTGRES_PASSWORD (default mlops)
  POSTGRES_HOST (default 127.0.0.1)
  POSTGRES_PORT (default 5432)
  POSTGRES_DB (default mlflow)

Table pipeline_console_jobs is created on first DB access so it stays separate from MLflow tables.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any
from urllib.parse import quote_plus

import psycopg
from psycopg.rows import dict_row

TABLE = "pipeline_console_jobs"

_WRITE_LOCK = threading.Lock()

_COLUMNS = (
    "id",
    "action",
    "status",
    "message",
    "error",
    "created_ts",
    "started_ts",
    "finished_ts",
    "duration_seconds",
    "download_count_requested",
    "seed_offset",
)

_DDL_TABLE = f"""CREATE TABLE IF NOT EXISTS {TABLE} (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    error TEXT,
    created_ts DOUBLE PRECISION,
    started_ts DOUBLE PRECISION,
    finished_ts DOUBLE PRECISION,
    duration_seconds DOUBLE PRECISION,
    download_count_requested INTEGER,
    seed_offset INTEGER
)"""

_DDL_INDEX = (
    f"CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_created_ts ON {TABLE} (created_ts DESC)"
)

_initialized_dsn: str | None = None
_init_lock = threading.Lock()


def _database_url() -> str:
    raw = os.getenv("DATABASE_URL")
    if raw and str(raw).strip():
        return str(raw).strip()
    user = os.getenv("POSTGRES_USER", "mlops")
    password = os.getenv("POSTGRES_PASSWORD", "mlops")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "mlflow")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{dbname}"


def _connect() -> psycopg.Connection:
    return psycopg.connect(
        _database_url(),
        row_factory=dict_row,
        connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10")),
        autocommit=False,
    )


def _ensure_schema() -> None:
    global _initialized_dsn

    dsn = _database_url()
    if dsn == _initialized_dsn:
        return
    with _init_lock:
        if dsn == _initialized_dsn:
            return
        with _connect() as conn:
            conn.execute(_DDL_TABLE)
            conn.execute(_DDL_INDEX)
            conn.commit()
        _initialized_dsn = dsn


def init_db() -> None:
    """Create pipeline jobs table/index if missing. Safe to call on startup."""
    _ensure_schema()


def insert_job(job: dict[str, Any]) -> None:
    init_db()
    cols = [c for c in _COLUMNS if c in job]
    placeholders = ", ".join("%s" for _ in cols)
    sql = f"INSERT INTO {TABLE} ({', '.join(cols)}) VALUES ({placeholders})"
    values = [job[c] for c in cols]
    with _WRITE_LOCK, _connect() as conn:
        conn.execute(sql, values)
        conn.commit()


def update_job(job_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return
    allowed = {k: v for k, v in kwargs.items() if k in _COLUMNS}
    if not allowed:
        return
    init_db()
    set_clause = ", ".join(f'{k} = %s' for k in allowed)
    values = list(allowed.values()) + [job_id]
    sql = f"UPDATE {TABLE} SET {set_clause} WHERE id = %s"
    with _WRITE_LOCK, _connect() as conn:
        conn.execute(sql, values)
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE} WHERE id = %s",
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def get_started_ts(job_id: str) -> float:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            f"SELECT started_ts FROM {TABLE} WHERE id = %s",
            (job_id,),
        ).fetchone()
    if row and row.get("started_ts") is not None:
        return float(row["started_ts"])
    return time.time()


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE} ORDER BY created_ts DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_all_jobs_for_tests() -> None:
    """Empty the jobs table (tests only)."""
    init_db()
    with _WRITE_LOCK, _connect() as conn:
        conn.execute(f"DELETE FROM {TABLE}")
        conn.commit()
