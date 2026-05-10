import os
import re
from pathlib import Path

import mlflow
from dotenv import load_dotenv
from ultralytics import YOLO


def train() -> None:
    # Load local .env so training works even in fresh shells.
    load_dotenv()
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("yolo-local-demo")

    data_yaml = Path("datasets/processed/data.yaml")
    if not data_yaml.exists():
        raise FileNotFoundError("Run dataset generation first: make data-generate")

    with mlflow.start_run() as run:
        mlflow.log_param("model", "yolov8n.pt")
        mlflow.log_param("epochs", 1)
        mlflow.log_param("imgsz", 320)

        model = YOLO("yolov8n.pt")
        results = model.train(data=str(data_yaml), epochs=1, imgsz=320, batch=4)

        metrics = getattr(results, "results_dict", {}) or {}
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                # MLflow metric names do not allow characters like parentheses.
                safe_key = re.sub(r"[^a-zA-Z0-9_./ -]", "_", str(k))
                mlflow.log_metric(safe_key, float(v))

        model_dir = Path("models")
        model_dir.mkdir(parents=True, exist_ok=True)
        model = YOLO("yolov8n.pt")
        try:
            model.export(format="onnx")
        except Exception as exc:
            # Keep tutorial flow moving even if optional ONNX export fails.
            mlflow.log_param("onnx_export_error", str(exc))
            print(f"ONNX export skipped: {exc}")
        mlflow.log_artifact(str(model_dir))
        print(f"Training completed. Run ID: {run.info.run_id}")


if __name__ == "__main__":
    train()
