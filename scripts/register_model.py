import argparse
import os

import mlflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--name", default="yolo-barcode-detector")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    uri = f"runs:/{args.run_id}/models"
    result = mlflow.register_model(uri, args.name)
    print(f"Registered: {result.name} v{result.version}")


if __name__ == "__main__":
    main()
