# Local MLOps Demo (Computer Vision, YOLOv8)

A beginner-to-intermediate, **hands-on** MLOps tutorial for local laptops using only open-source tools.

Use case: lightweight object detection (barcode/box-like synthetic dataset + optional real dataset).

---

## 1) High-Level Architecture

```mermaid
flowchart LR
  A[Raw Images + Labels] --> B[DVC Versioned Dataset]
  B --> C[Prefect Pipeline Validate Train Evaluate]
  C --> D[YOLOv8 Training on PyTorch]
  D --> E[MLflow Tracking Registry Postgres MinIO]
  E --> F[Model Packaging BentoML]
  F --> G[FastAPI Inference API]
  G --> H[Kubernetes Deployment Helm Manifests]
  H --> I[Prometheus + Grafana]
  H --> J[Loki Logs]
  H --> K[OpenTelemetry Traces]
  L[GitHub Actions CI/CD] --> H
  M[Redpanda Stream] --> G
```

---

## 2) Why each tool?

- **Podman / Podman Compose**: Docker-compatible local containers, daemonless.
- **kind**: lightweight local Kubernetes cluster using container nodes.
- **Helm**: reusable app packaging/deploy patterns.
- **PyTorch + YOLOv8**: approachable object detection training.
- **MLflow**: experiments + model registry.
- **Prefect**: local-first orchestration (simple flow authoring).
- **DVC**: dataset and model versioning in Git workflows.
- **MinIO + PostgreSQL**: artifact/object storage + metadata DB.
- **FastAPI + BentoML**: practical API serving and packaging style.
- **Prometheus/Grafana/Loki/OTel**: metrics, dashboards, logs, traces.
- **Redpanda**: lightweight Kafka-compatible streaming.
- **Terraform**: IaC patterns (local Kubernetes resources via providers).
- **GitHub Actions**: CI/CD automation patterns.

---

## 3) Prerequisites

- macOS/Linux laptop (8 GB RAM minimum, 16 GB recommended)
- Python 3.11+
- Git
- Podman 5+
- podman-compose
- kubectl
- kind
- helm
- dvc
- terraform
- uv

### Install (macOS example)

```bash
brew install podman podman-compose kubectl kind helm dvc terraform uv
podman machine init
podman machine start
```

Verify:

```bash
podman --version
podman-compose --version
kubectl version --client
kind version
helm version
dvc --version
terraform --version
uv --version
```

---

## 4) Local environment setup

```bash
git clone git@github.com:skoli0/object-detection-ml-pipeline.git
cd object-detection-ml-pipeline
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Discover Makefile shortcuts (the default `make` target prints the same list):

```bash
make help
```

Configure local env:

```bash
cp .env.example .env
```

---

## 5) Project structure

```text
mlops-demo/
├── app/
├── pipelines/
├── models/
├── datasets/
├── infrastructure/
├── kubernetes/
├── monitoring/
├── scripts/
├── tests/
├── .github/workflows/
├── podman-compose.yml
├── Makefile
└── README.md
```

---

## 6) Start local platform services (Podman Compose)

```bash
make infra-up
```

### URLs to open (local defaults)

Use these after `make infra-up`. For the browser console and OpenAPI, also run `make serve-local` (API on **8000**).

If you change **`MLFLOW_PORT`** / **`MLFLOW_TRACKING_URI`** in `.env` (e.g. **5050** when macOS AirPlay uses **5000**), open MLflow on that host port instead of **5000**.

**Infra (Podman Compose — browser / UIs)**

| Service | URL |
|--------|-----|
| MLflow UI | <http://127.0.0.1:5000/> (or `http://127.0.0.1:${MLFLOW_PORT:-5000}/` from `.env`) |
| Prefect UI | <http://127.0.0.1:4200/> |
| MinIO Console | <http://127.0.0.1:9001/> |

Prefect: keep **`PREFECT_API_URL=http://127.0.0.1:4200/api`** in `.env` when using the Compose server; image is **Prefect 3** to match the Python client. Without that URL, ephemeral runs do not appear in the Prefect UI.

**Infra (clients / non-browser)**

| Service | Address |
|--------|---------|
| MinIO S3 API | `http://127.0.0.1:9000` (same as `MLFLOW_S3_ENDPOINT_URL` in `.env`) |
| PostgreSQL | `127.0.0.1:5432` |
| Prefect REST API | <http://127.0.0.1:4200/api> |
| Redpanda (Kafka) | `127.0.0.1:9092` |

**FastAPI (`make serve-local`)**

| What | URL |
|------|-----|
| Pipeline console | <http://127.0.0.1:8000/ui> |
| Swagger UI | <http://127.0.0.1:8000/docs> |
| ReDoc | <http://127.0.0.1:8000/redoc> |
| OpenAPI schema | <http://127.0.0.1:8000/openapi.json> |
| Health | <http://127.0.0.1:8000/health> |
| Prometheus metrics | <http://127.0.0.1:8000/metrics> |
| Pipeline UI config (JSON) | <http://127.0.0.1:8000/api/pipeline/config> |
| List pipeline jobs (JSON) | <http://127.0.0.1:8000/api/pipeline/jobs> |
| Single pipeline job (JSON) | <http://127.0.0.1:8000/api/pipeline/jobs/{job_id}> |
| Create pipeline job | `POST` <http://127.0.0.1:8000/api/pipeline/jobs> |
| Inference | `POST` <http://127.0.0.1:8000/predict> |

**Kubernetes** (after `make k8s-deploy`): ports depend on manifests; use `kubectl get svc -n mlops-demo` and `kubectl port-forward` as needed for Grafana/Prometheus/Loki.

Create MinIO bucket:

```bash
make minio-bootstrap
```

### Cleanup: stop services, remove containers, Kubernetes

List available automation targets:

```bash
make help
```

**Podman Compose (platform containers)**

- **Stop containers but keep data** (named volumes for Postgres and MinIO remain for next `make infra-up`):

  ```bash
  make infra-down
  ```

- **Stop and remove containers plus Compose volumes** (full reset of local MinIO/Postgres data; Redpanda state is also cleared):

  ```bash
  make infra-clean
  ```

  Equivalent manual commands from this directory: `podman-compose down` and `podman-compose down -v --remove-orphans`.

**Local FastAPI server**

- If you ran `make serve-local`, stop it with **Ctrl+C** in that terminal.

**Podman machine (VM that runs the Linux engine on macOS)**

- Stop the VM when you are done for the day (frees CPU/RAM):

  ```bash
  podman machine stop
  ```

  Start again before the next `make infra-up`: `podman machine start`.

**Kubernetes (kind)**

- Delete the whole local cluster created by `make k8s-create`:

  ```bash
  kind delete cluster --name mlops-local
  ```

- If you keep kind running but want to remove only this project’s resources:

  ```bash
  kubectl delete namespace mlops-demo --ignore-not-found=true
  ```

**Helm release** (if you used section 13)

```bash
helm uninstall mlops-demo -n mlops-demo 2>/dev/null || true
```

---

## 7) Dataset ingestion + validation + DVC versioning

Generate tiny synthetic barcode/box dataset (fast for laptops):

```bash
make data-generate
make data-validate
```

Track with DVC:

```bash
make dvc-init
make dvc-track
```

> Optional: replace `datasets/raw` with a tiny Roboflow/Open Images sample and keep same label format.

---

## 8) Train YOLOv8 (CPU/GPU)

```bash
make train
```

GPU note:
- If CUDA is available, Ultralytics auto-detects GPU.
- Otherwise, this tutorial defaults to CPU-safe tiny training.

Training logs and metrics go to MLflow.

---

## 9) Pipeline orchestration (Prefect)

Run full flow:

```bash
make pipeline-run
```

Flow steps:
1. validate dataset
2. train YOLOv8 model
3. register model metadata in MLflow
4. export service-ready artifact

---

## 10) Model registry usage (MLflow)

- Open MLflow UI: <http://127.0.0.1:5000/> (or the port from `.env`; see **§6 URLs to open**).
- Promote models by stage (`Staging` -> `Production`) in UI.

Command-line registration helper:

```bash
python scripts/register_model.py --run-id <RUN_ID> --name yolo-barcode-detector
```

---

## 11) Serve model locally (FastAPI + BentoML)

```bash
make serve-local
```

- **Pipeline console:** <http://127.0.0.1:8000/ui> — download web images, validate, train, or run the full Prefect flow; REST details in <http://127.0.0.1:8000/docs> (see **§6 URLs to open**).
- **Predict (curl):**

```bash
curl -X POST "http://127.0.0.1:8000/predict" -F "file=@datasets/raw/images/sample_0.jpg"
```

---

## 12) Kubernetes local cluster setup

```bash
make k8s-create
make k8s-deploy
```

This installs:
- app deployment/service
- Prometheus/Grafana/Loki (lightweight local stack)

Check:

```bash
kubectl get pods -A
kubectl get svc -n mlops-demo
```

---

## 13) Helm deployment

```bash
helm upgrade --install mlops-demo ./infrastructure/helm/mlops-demo -n mlops-demo --create-namespace
```

Production pattern: use Helm values for environment-specific overrides (dev/staging/prod).

---

## 14) Observability setup

### Metrics (Prometheus)
- FastAPI exposes `/metrics` via `prometheus-fastapi-instrumentator`.

### Dashboards (Grafana)
- Add Prometheus + Loki datasources.
- Import sample dashboard JSON from `monitoring/grafana-dashboard.json`.

### Logs (Loki)
- Promtail collects Kubernetes logs and forwards to Loki.

### Traces (OpenTelemetry)
- API emits traces to OTel Collector.
- Collector exports to logging by default (local-friendly).

---

## 15) Streaming inference (Redpanda)

Producer sends image event messages:

```bash
python scripts/produce_events.py
```

Consumer in API (optional) reads events and triggers prediction pipeline pattern.

---

## 16) CI/CD (GitHub Actions)

Workflow: `.github/workflows/ci-cd.yaml`
- lint + tests
- train smoke check
- build image with Podman
- (optional) deploy to local K8s/self-hosted runner

---

## 17) Drift detection basics

Run baseline drift check (size/brightness proxy stats):

```bash
python scripts/drift_check.py --reference datasets/processed/reference_stats.json --current datasets/processed/current_stats.json
```

Production pattern: replace proxies with embedding/statistical drift libraries (Evidently, NannyML).

---

## 18) Canary deployment basics

Apply canary manifests:

```bash
kubectl apply -f kubernetes/base/canary.yaml
```

Pattern shown:
- stable deployment: 90%
- canary deployment: 10%
- switch traffic by adjusting service selectors/weights (service-mesh recommended in production).

---

## 19) Rollback example

```bash
kubectl rollout history deployment/mlops-api -n mlops-demo
kubectl rollout undo deployment/mlops-api -n mlops-demo
```

Helm rollback:

```bash
helm history mlops-demo -n mlops-demo
helm rollback mlops-demo 1 -n mlops-demo
```

---

## 20) Complete execution walkthrough

```bash
make setup
make infra-up
make minio-bootstrap
make data-generate
make data-validate
make dvc-init
make dvc-track
make train
make pipeline-run
make serve-local
make k8s-create
make k8s-deploy
```

---

## Common beginner mistakes

- Not starting `podman machine` before compose commands.
- Forgetting `.env` values for S3/MLflow.
- Training with huge datasets locally (slow, memory pressure).
- Skipping DVC, then losing dataset reproducibility.
- No health/readiness probes in Kubernetes.
- No rollback plan before canary/testing.

---

## Troubleshooting

- **Podman socket issues**: restart `podman machine`.
- **MLflow can't write artifacts**: verify MinIO bucket and env vars.
- **K8s image pull fails**: load image into kind (`kind load docker-image ...`) or use local registry.
- **Grafana empty dashboards**: check Prometheus scrape target `/metrics`.
- **Redpanda connection errors**: verify `localhost:9092` mapped and broker up.

---

## Scaling recommendations

- Move MinIO/Postgres to managed services in cloud.
- Use remote DVC storage and object lifecycle policies.
- Add model approval gates in CI/CD.
- Replace basic canary with service mesh (Istio/Linkerd + progressive delivery).
- Add feature store and richer drift/quality monitoring.

---

## Next learning steps

- Add automated retraining triggers from drift alerts.
- Introduce KServe for model serving on Kubernetes.
- Add vector/embedding monitoring for vision models.
- Expand to multi-model A/B experimentation.
