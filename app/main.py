import io
import os
from typing import Any

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="MLOps Demo CV API", version="0.1.0")
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
