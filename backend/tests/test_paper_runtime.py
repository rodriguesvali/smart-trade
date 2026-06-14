import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import (
    CandleFeatureRecord,
    CandleRecord,
    FeatureSchemaRecord,
    ModelRegistryRecord,
    OrderRecord,
    PositionRecord,
    StrategyDecisionRecord,
)
from smart_trade_backend.application.paper.runtime import (
    PaperRuntimeError,
    run_paper_replay,
)
from smart_trade_backend.application.strategy.registry import (
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


class RuleProbabilityModel:
    def predict_probability(self, values: dict[str, float], feature_names: list[str]) -> float:
        return 0.9


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def seed_strategy_features_and_candles(client: TestClient) -> None:
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
        strategy = register_available_strategies(session)[0]
        session.commit()
        select_strategy(
            session,
            get_settings(),
            strategy_registry_id=strategy.id,
            parameters={"take_profit_pct": 0.20},
        )
        seed_runtime_rows(session)


def seed_runtime_rows(session) -> None:
    start = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
    closes = [
        Decimal("100"),
        Decimal("104"),
        Decimal("106"),
        Decimal("105"),
        Decimal("101"),
    ]
    for index, close_price in enumerate(closes):
        opened_at = start + timedelta(minutes=index)
        open_time_ms = int(opened_at.timestamp() * 1000)
        session.add(
            CandleRecord(
                exchange="bybit",
                symbol="BTC/USDT",
                timeframe="1m",
                open_time_ms=open_time_ms,
                opened_at=opened_at,
                open=close_price,
                high=close_price + Decimal("1"),
                low=close_price - Decimal("1"),
                close=close_price,
                volume=Decimal("1"),
                source="test",
                is_closed=True,
                raw_payload=[],
            )
        )
        session.add(
            CandleFeatureRecord(
                exchange="bybit",
                symbol="BTC/USDT",
                timeframe="1m",
                feature_schema_id="b3-talib-basic-v1",
                open_time_ms=open_time_ms,
                candle_opened_at=opened_at,
                values={
                    "rsi_14": 20.0 if index == 0 else 60.0,
                    "bb_upper_20_2": float(close_price) + 3,
                    "bb_middle_20": float(close_price),
                    "bb_lower_20_2": float(close_price) - 3,
                    "return_1": 0.01,
                    "log_return_1": 0.009,
                    "volume_change_1": 0.0,
                    "atr_14": 1.0,
                    "body_pct": 0.1,
                },
            )
        )
    session.commit()


def seed_approved_model(client: TestClient) -> None:
    with client.app.state.db_session_factory() as session:
        session.add(
            ModelRegistryRecord(
                model_id="approved-entry-model",
                model_role="entry_confirmation",
                strategy_id="default_rsi_xgboost_long",
                strategy_version="1.0.0",
                asset_symbol="BTC/USDT",
                timeframe="1m",
                feature_schema_id="b3-talib-basic-v1",
                status="APPROVED",
                artifact_uri="test-model.json",
                metrics={},
                parameters={},
                approved_at=datetime(2026, 6, 14, tzinfo=UTC),
            )
        )
        session.commit()


def test_paper_runtime_requires_approved_model() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_features_and_candles(client)
        with client.app.state.db_session_factory() as session:
            try:
                run_paper_replay(session, get_settings(), probability_model=RuleProbabilityModel())
            except PaperRuntimeError as exc:
                error = str(exc)

    assert "No compatible approved or active model" in error


def test_paper_runtime_creates_long_position_and_simulated_records() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_features_and_candles(client)
        seed_approved_model(client)
        with client.app.state.db_session_factory() as session:
            result = run_paper_replay(
                session,
                get_settings(),
                probability_model=RuleProbabilityModel(),
            )
            decisions = session.query(StrategyDecisionRecord).count()
            orders = session.query(OrderRecord).count()
            positions = session.query(PositionRecord).count()
            position = session.query(PositionRecord).one()

    assert result.processed_candles == 5
    assert decisions >= 5
    assert orders == 2
    assert positions == 1
    assert position.side == "LONG"
    assert position.status == "CLOSED"
    assert position.model_refs[0]["model_id"] == "approved-entry-model"
    assert position.stop_loss_price >= position.average_entry_price


def test_paper_runtime_is_idempotent_for_processed_candles() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_features_and_candles(client)
        seed_approved_model(client)
        with client.app.state.db_session_factory() as session:
            first = run_paper_replay(
                session,
                get_settings(),
                probability_model=RuleProbabilityModel(),
            )
            second = run_paper_replay(
                session,
                get_settings(),
                probability_model=RuleProbabilityModel(),
            )
            orders = session.query(OrderRecord).count()
            positions = session.query(PositionRecord).count()

    assert first.processed_candles == 5
    assert second.processed_candles == 0
    assert orders == 2
    assert positions == 1
