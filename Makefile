SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
UV := uv

.PHONY: setup infra-up infra-down minio-bootstrap data-generate data-validate dvc-init dvc-track train pipeline-run serve-local k8s-create k8s-deploy test lint

$(PY):
	@if [ -d "$(VENV)" ] && [ ! -f "$(VENV)/pyvenv.cfg" ]; then \
		echo "Invalid $(VENV) found, recreating..."; \
		rm -rf "$(VENV)"; \
	fi
	$(UV) venv --seed $(VENV)
	$(UV) pip install --python $(PY) -r requirements.txt

setup: $(PY)

infra-up:
	podman-compose up -d

infra-down:
	podman-compose down

minio-bootstrap:
	bash scripts/bootstrap_minio.sh

data-generate: $(PY)
	$(PY) scripts/generate_dataset.py

data-validate: $(PY)
	$(PY) scripts/validate_data.py

dvc-init:
	@if [ ! -d ".git" ]; then \
		echo "Git repo not found, running git init..."; \
		git init; \
	fi
	dvc init -f

dvc-track: $(PY)
	dvc repro generate_data validate_data
	git add dvc.yaml dvc.lock datasets/.gitignore datasets/processed/.gitignore || true

train: $(PY)
	$(PY) -m pipelines.train

pipeline-run: $(PY)
	$(PY) -m pipelines.prefect_flow

serve-local: $(PY)
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

k8s-create:
	kind create cluster --name mlops-local || true

k8s-deploy:
	kubectl apply -f kubernetes/base/namespace.yaml
	kubectl apply -k kubernetes/base

test: $(PY)
	$(VENV)/bin/pytest -q

lint: $(PY)
	$(VENV)/bin/ruff check .
