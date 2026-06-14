import os

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import FeatureSchemaRecord
from smart_trade_backend.application.strategy.registry import (
    StrategySelectionError,
    register_available_strategies,
    select_strategy,
)
from smart_trade_backend.config import get_settings
from smart_trade_backend.db import Base
from smart_trade_backend.main import app

DEFAULT_B3_FEATURES = [
    "rsi_14",
    "bb_upper_20_2",
    "bb_middle_20",
    "bb_lower_20_2",
    "return_1",
    "log_return_1",
    "volume_change_1",
    "atr_14",
    "body_pct",
]


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def add_b3_feature_schema(client: TestClient) -> None:
    with client.app.state.db_session_factory() as session:
        session.add(
            FeatureSchemaRecord(
                schema_id="b3-talib-basic-v1",
                name="talib_basic",
                version="1.0.0",
                timeframe="1m",
                features=DEFAULT_B3_FEATURES,
                parameters={"source": "test"},
            )
        )
        session.commit()


def test_default_strategy_registers_with_required_contract() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        with client.app.state.db_session_factory() as session:
            records = register_available_strategies(session)

    assert len(records) == 1
    assert records[0].strategy_id == "default_rsi_xgboost_long"
    assert records[0].required_features == DEFAULT_B3_FEATURES
    assert records[0].model_roles[0]["role"] == "entry_confirmation"


def test_strategy_selection_fails_without_required_feature_schema() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings()
        with client.app.state.db_session_factory() as session:
            strategy = register_available_strategies(session)[0]
            try:
                select_strategy(session, settings, strategy_registry_id=strategy.id)
            except StrategySelectionError as exc:
                error = str(exc)

    assert "Missing required features" in error


def test_strategy_can_be_selected_when_runtime_is_compatible() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        add_b3_feature_schema(client)
        response = client.get("/api/strategies")
        strategy_id = response.json()["items"][0]["id"]

        selection_response = client.post(
            "/api/strategies/select",
            json={"strategy_registry_id": strategy_id, "parameters": {"oversold_threshold": 28}},
        )
        status_response = client.get("/api/operation/status")

    assert selection_response.status_code == 201
    assert selection_response.json()["status"] == "SELECTED"
    assert selection_response.json()["parameters"]["oversold_threshold"] == 28
    assert "No selected strategy." not in status_response.json()["blockers"]
