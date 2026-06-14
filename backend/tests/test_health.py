import os
from datetime import UTC, datetime

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import OperationalEventRecord
from smart_trade_backend.db import Base
from smart_trade_backend.main import app


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_b1_read_contracts_return_empty_state() -> None:
    with TestClient(app) as client:
        prepare_schema(client)

        config_response = client.get("/api/configuration/summary")
        strategies_response = client.get("/api/strategies")
        models_response = client.get("/api/models")
        operation_response = client.get("/api/operation/status")
        events_response = client.get("/api/events")

    assert config_response.status_code == 200
    assert config_response.json()["symbol"] == "BTC/USDT"
    assert config_response.json()["timeframe"] == "1m"
    assert strategies_response.status_code == 200
    assert strategies_response.json()["selected_strategy_id"] is None
    assert strategies_response.json()["items"][0]["strategy_id"] == "default_rsi_xgboost_long"
    assert strategies_response.json()["items"][0]["compatibility"]["compatible"] is False
    assert models_response.status_code == 200
    assert models_response.json() == {"items": []}
    assert operation_response.status_code == 200
    assert operation_response.json()["state"] == "NOT_READY"
    assert "No selected strategy." in operation_response.json()["blockers"]
    assert events_response.status_code == 200
    assert events_response.json() == {"items": []}


def test_command_request_is_persisted_and_auditable() -> None:
    with TestClient(app) as client:
        prepare_schema(client)

        response = client.post(
            "/api/commands",
            json={
                "command_type": "RETRAIN_MODEL",
                "requested_by": "operator",
                "payload": {"reason": "contract-test"},
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["command_type"] == "RETRAIN_MODEL"
    assert body["status"] == "REQUESTED"
    assert body["payload"] == {"reason": "contract-test"}


def test_events_are_returned_latest_first() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        with client.app.state.db_session_factory() as session:
            session.add(
                OperationalEventRecord(
                    event_type="schema_ready",
                    severity="INFO",
                    source="test",
                    message="B1 schema is ready.",
                    details={},
                    occurred_at=datetime(2026, 6, 14, tzinfo=UTC),
                )
            )
            session.commit()

        response = client.get("/api/events")

    assert response.status_code == 200
    assert response.json()["items"][0]["event_type"] == "schema_ready"
