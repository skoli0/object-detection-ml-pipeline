import io
import os
from typing import Any

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from PIL import Image
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry, generate_latest, multiprocess
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response

from app.pipeline_router import get_dashboard_html, router as pipeline_router

app = FastAPI(title="MLOps Demo CV API", version="0.1.0")
app.include_router(pipeline_router)
Instrumentator().instrument(app)


def _metrics_response() -> Response:
    registry = REGISTRY
    if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@app.get("/metrics", tags=["monitoring"])
def prometheus_metrics() -> Response:
    """Prometheus scrape endpoint (histograms/counters from instrumentator middleware)."""
    return _metrics_response()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ui", include_in_schema=False)
def pipeline_control_ui() -> HTMLResponse:
    """Trigger downloads, Prefect flows, or training from the browser."""
    return HTMLResponse(get_dashboard_html())


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
        arr = np.array(image)
        # Lightweight placeholder prediction to keep local demo fast.
        score = float(arr.mean() / 255.0)
        label = "barcode_or_box" if score > 0.3 else "background"
        return {
            "filename": file.filename,
            "prediction": [{"label": label, "confidence": round(score, 4)}],
            "model": os.getenv("MODEL_NAME", "yolo-barcode-detector"),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
