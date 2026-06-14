import os

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
