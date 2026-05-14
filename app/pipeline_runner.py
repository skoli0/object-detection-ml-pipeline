"""Run CLI pipeline stages from the API (cwd = project root)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> None:
    subprocess.run(
        [sys.executable, *args],
        cwd=str(PROJECT_ROOT),
        check=True,
    )


def run_download_web_images(count: int, seed_offset: int) -> None:
    script = PROJECT_ROOT / "scripts" / "download_web_images.py"
    _run([str(script), "--count", str(count), "--seed-offset", str(seed_offset)])


def run_validate_data() -> None:
    script = PROJECT_ROOT / "scripts" / "validate_data.py"
    _run([str(script)])


def run_train() -> None:
    _run(["-m", "pipelines.train"])


def run_prefect_flow() -> None:
    _run(["-m", "pipelines.prefect_flow"])
