#!/usr/bin/env bash
set -euo pipefail

podman run --rm --network host --entrypoint /bin/sh quay.io/minio/mc:latest -c "mc alias set local http://127.0.0.1:9000 minio minio123 && mc mb -p local/mlflow || true"

echo "MinIO bucket 'mlflow' ensured."
