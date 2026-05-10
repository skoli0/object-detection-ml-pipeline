"""Prefect orchestration for validate + train.

Without ``PREFECT_API_URL``, Prefect 3 uses a transient local API (no ``prefect server``
or compose service required). Set ``PREFECT_API_URL`` when you run a real Prefect API
(e.g. uncomment the ``prefect`` service in ``podman-compose.yml``).
"""

import os

from dotenv import load_dotenv

load_dotenv()

if os.environ.get("PREFECT_API_URL", "").strip():
    # Use the long-lived server (e.g. compose on :4200); do not also force ephemeral mode.
    os.environ.pop("PREFECT_SERVER_ALLOW_EPHEMERAL_MODE", None)
else:
    # Laptop-only: transient API subprocess (nothing to show on http://localhost:4200).
    os.environ.setdefault("PREFECT_SERVER_ALLOW_EPHEMERAL_MODE", "true")

from prefect import flow, task

from pipelines.train import train
from scripts.validate_data import validate_dataset


@task
def validate_task() -> None:
    validate_dataset()


@task
def train_task() -> None:
    train()


@flow(name="cv-mlops-pipeline")
def cv_pipeline() -> None:
    validate_task()
    train_task()


if __name__ == "__main__":
    cv_pipeline()
