from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_pipeline_ui_served() -> None:
    client = TestClient(app)
    res = client.get("/ui")
    assert res.status_code == 200
    assert b"Pipeline Console" in res.content


def test_metrics_prometheus_format() -> None:
    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.text
    assert "http_requests_total" in body or "# TYPE " in body
