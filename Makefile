SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
UV := uv
# Re-run `uv pip install` when requirements.txt changes (see $(PIP_STAMP)).
PIP_STAMP := $(VENV)/.requirements-installed

# Plain `make` runs the full local stack + data + train + tests (see `all`).
.DEFAULT_GOAL := all

ifneq (,$(wildcard .env))
include .env
export
endif

# container_name entries in podman-compose.yml — clear these if compose failed mid-flight.
COMPOSE_CONTAINER_NAMES := mlops-postgres mlops-minio mlops-mlflow mlops-prefect mlops-redpanda

.PHONY: all env help setup podman-ready infra-up infra-reset infra-down infra-clean infra-wait prefect-wait minio-bootstrap dvc-bootstrap data-generate data-validate dvc-init dvc-track train pipeline-run serve-local k8s-create k8s-deploy test lint

help: ## List all Makefile targets
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z0-9_.-]+:.*##/ { sub(/^ +/, "", $$2); printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' "$(firstword $(MAKEFILE_LIST))" | sort

$(PY):
	@if [ -d "$(VENV)" ] && [ ! -f "$(VENV)/pyvenv.cfg" ]; then \
		echo "Invalid $(VENV) found, recreating..."; \
		rm -rf "$(VENV)"; \
	fi
	@if [ ! -x "$(PY)" ]; then \
		$(UV) venv --seed $(VENV); \
	fi

$(PIP_STAMP): requirements.txt $(PY)
	$(UV) pip install --python $(PY) -r requirements.txt
	@touch "$(PIP_STAMP)"

setup: $(PIP_STAMP) ## Create venv (uv) and install Python dependencies

# Full local path: env file, venv, Compose, MinIO bucket, DVC data stages, Prefect flow, pytest.
all: env setup infra-up minio-bootstrap infra-wait prefect-wait dvc-bootstrap dvc-track pipeline-run test ## End-to-end local build (default goal for `make`)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	echo "Done. MLflow: http://127.0.0.1:$${MLFLOW_PORT:-5000}/ — Prefect UI: http://127.0.0.1:4200/ — API: make serve-local"

env: ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then \
		cp .env.example .env && echo "Created .env from .env.example"; \
	fi

# Ensures Podman API is reachable (starts the macOS VM when needed).
podman-ready:
	@if [ "$$(uname -s)" = "Darwin" ] && ! podman info >/dev/null 2>&1; then \
		echo "Starting Podman machine..."; \
		podman machine start; \
	fi
	@podman info >/dev/null 2>&1 || { \
		echo "Podman is not reachable. macOS: run \`podman machine init && podman machine start\`. Linux: start the Podman service/socket." >&2; \
		exit 1; \
	}

infra-up: podman-ready ## Start Podman Compose stack (Postgres, MinIO, MLflow, Prefect, Redpanda)
	podman-compose up -d

# After errors like “container name is already in use” or broken pod membership.
infra-reset: podman-ready ## Down orphans, prune pods, recreate stack (keeps volumes)
	podman-compose down --remove-orphans 2>/dev/null || true
	@for c in $(COMPOSE_CONTAINER_NAMES); do podman rm -f "$$c" 2>/dev/null || true; done
	@podman pod prune -f 2>/dev/null || true
	podman-compose up -d

infra-down: ## Stop Compose containers (keeps named volumes / data)
	podman-compose down --remove-orphans

infra-clean: podman-ready ## Stop Compose, remove containers and volumes (full local infra reset)
	podman-compose down -v --remove-orphans 2>/dev/null || true
	@for c in $(COMPOSE_CONTAINER_NAMES); do podman rm -f "$$c" 2>/dev/null || true; done
	@podman pod prune -f 2>/dev/null || true

minio-bootstrap: ## Create MinIO bucket for MLflow artifacts
	bash scripts/bootstrap_minio.sh

# Wait until MLflow responds (uses MLFLOW_PORT from .env when present).
infra-wait: ## Poll MLflow UI until it answers (used by `make all`)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	port=$${MLFLOW_PORT:-5000}; \
	echo "Waiting for MLflow at http://127.0.0.1:$${port}/ ..."; \
	for i in $$(seq 1 45); do \
		if curl -sf "http://127.0.0.1:$${port}/" >/dev/null 2>&1; then \
			echo "MLflow is up."; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Warning: MLflow did not respond in time; training may fail until the server is ready." >&2

# Wait for compose Prefect API (skip if you use ephemeral mode with PREFECT_API_URL unset).
prefect-wait: ## Poll Prefect API until it answers (used by `make all`)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	if [ -z "$${PREFECT_API_URL:-}" ] || [ "$${PREFECT_API_URL:-}" = "" ]; then \
		echo "PREFECT_API_URL unset; skipping Prefect wait (ephemeral flow run)."; \
		exit 0; \
	fi; \
	echo "Waiting for Prefect API at $${PREFECT_API_URL%/}/ ..."; \
	base=$${PREFECT_API_URL%/api}; \
	for i in $$(seq 1 60); do \
		if curl -sf "$${base}/api/admin/version" >/dev/null 2>&1 || curl -sf "$${base}/api/health" >/dev/null 2>&1 || curl -sf "http://127.0.0.1:4200/api/admin/version" >/dev/null 2>&1; then \
			echo "Prefect server is up."; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Warning: Prefect API not ready; dashboard may stay empty until the server starts." >&2

data-generate: $(PIP_STAMP) ## Generate synthetic dataset under datasets/
	$(PY) scripts/generate_dataset.py

data-validate: $(PIP_STAMP) ## Run dataset validation checks
	$(PY) scripts/validate_data.py

dvc-init: ## Initialize Git (if needed) and DVC in this directory
	@if [ ! -d ".git" ]; then \
		echo "Git repo not found, running git init..."; \
		git init; \
	fi
	dvc init -f

dvc-bootstrap: ## Run dvc-init when .dvc is missing (used by `make all`)
	@if [ ! -d .dvc ]; then \
		$(MAKE) dvc-init; \
	fi

dvc-track: $(PIP_STAMP) ## Run DVC pipeline for data stages and stage lockfile updates
	dvc repro generate_data validate_data
	git add dvc.yaml dvc.lock datasets/.gitignore datasets/processed/.gitignore || true

train: $(PIP_STAMP) ## Train YOLOv8 via pipelines.train
	$(PY) -m pipelines.train

pipeline-run: $(PIP_STAMP) ## Run Prefect flow (pipelines.prefect_flow)
	$(PY) -m pipelines.prefect_flow

serve-local: $(PIP_STAMP) ## Run FastAPI app with uvicorn on :8000
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

k8s-create: ## Create local kind cluster (mlops-local)
	kind create cluster --name mlops-local || true

k8s-deploy: ## Apply Kubernetes manifests under kubernetes/base
	kubectl apply -f kubernetes/base/namespace.yaml
	kubectl apply -k kubernetes/base

test: $(PIP_STAMP) ## Run pytest
	$(VENV)/bin/pytest -q

lint: $(PIP_STAMP) ## Run ruff linter
	$(VENV)/bin/ruff check .
