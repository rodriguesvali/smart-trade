import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import (
    BacktestTradeRecord,
    CandleFeatureRecord,
    CandleRecord,
    FeatureSchemaRecord,
    ModelRegistryRecord,
    WalkForwardWindowRecord,
)
from smart_trade_backend.application.model_training.service import (
    ModelApprovalError,
    TrainingRow,
    approve_model,
    backtest_trades_for_model,
    train_selected_strategy_models,
    walk_forward_windows_for_model,
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


class RuleBasedTrainer:
    def fit(self, rows: list[TrainingRow], feature_names: list[str]):
        return RuleBasedModel()


class RuleBasedModel:
    model_type = "test.rule_based"
    parameters = {"rule": "rsi_14 <= 30"}

    def predict_probabilities(
        self, rows: list[TrainingRow], feature_names: list[str]
    ) -> list[float]:
        return [0.9 if row.values["rsi_14"] <= 30 else 0.1 for row in rows]

    def save(self, artifact_path: Path) -> None:
        artifact_path.write_text(json.dumps({"model_type": self.model_type}), encoding="utf-8")


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def seed_strategy_and_features(client: TestClient) -> None:
    settings = get_settings()
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
        select_strategy(session, settings, strategy_registry_id=strategy.id)
        seed_training_rows(session)


def seed_training_rows(session) -> None:
    start = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
    close = Decimal("100")
    closes: list[Decimal] = []
    for index in range(121):
        closes.append(close)
        if index % 10 == 0:
            close += Decimal("5")
        else:
            close -= Decimal("0.10")

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
        if index < 120:
            rsi = 20.0 if index % 10 == 0 else 60.0
            session.add(
                CandleFeatureRecord(
                    exchange="bybit",
                    symbol="BTC/USDT",
                    timeframe="1m",
                    feature_schema_id="b3-talib-basic-v1",
                    open_time_ms=open_time_ms,
                    candle_opened_at=opened_at,
                    values={
                        "rsi_14": rsi,
                        "bb_upper_20_2": float(close_price) + 3,
                        "bb_middle_20": float(close_price),
                        "bb_lower_20_2": float(close_price) - 3,
                        "return_1": 0.01 if rsi <= 30 else -0.001,
                        "log_return_1": 0.009 if rsi <= 30 else -0.001,
                        "volume_change_1": 0.0,
                        "atr_14": 1.0,
                        "body_pct": 0.1,
                    },
                )
            )
    session.commit()


def test_training_creates_backtested_model_with_temporal_evidence(tmp_path) -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_and_features(client)
        settings = get_settings().model_copy(
            update={
                "model_artifact_dir": str(tmp_path),
                "model_training_min_rows": 90,
                "model_holdout_min_rows": 20,
            }
        )
        with client.app.state.db_session_factory() as session:
            models = train_selected_strategy_models(
                session,
                settings,
                trainer=RuleBasedTrainer(),
            )
            model = models[0]
            windows = walk_forward_windows_for_model(session, model.model_id)
            trades = backtest_trades_for_model(session, model.model_id)
            persisted_window_count = session.query(WalkForwardWindowRecord).filter_by(
                model_id=model.model_id
            ).count()
            persisted_trade_count = session.query(BacktestTradeRecord).filter_by(
                model_id=model.model_id
            ).count()

    assert model.status == "BACKTESTED"
    assert model.model_role == "entry_confirmation"
    assert model.strategy_id == "default_rsi_xgboost_long"
    assert model.strategy_version == "1.0.0"
    assert model.asset_symbol == "BTC/USDT"
    assert model.timeframe == "1m"
    assert model.feature_schema_id == "b3-talib-basic-v1"
    assert model.training_window_end < model.holdout_start
    assert model.metrics["precision_class_1"] == 1.0
    assert model.metrics["trade_count"] >= 1
    assert model.metrics["profit_factor"] >= 1.0
    assert "max_drawdown" in model.metrics
    assert "win_rate" in model.metrics
    assert "max_losing_streak" in model.metrics
    assert model.metrics["acceptable_walk_forward_windows"] >= 1
    assert windows[0].train_end < windows[0].validation_start
    assert persisted_window_count == len(windows)
    assert persisted_trade_count == len(trades) == model.metrics["trade_count"]
    assert Path(model.artifact_uri).exists()


def test_model_approval_is_blocked_until_thresholds_pass(tmp_path) -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings().model_copy(update={"model_artifact_dir": str(tmp_path)})
        with client.app.state.db_session_factory() as session:
            weak = ModelRegistryRecord(
                model_id="weak-model",
                model_role="entry_confirmation",
                strategy_id="default_rsi_xgboost_long",
                strategy_version="1.0.0",
                asset_symbol="BTC/USDT",
                timeframe="1m",
                feature_schema_id="b3-talib-basic-v1",
                status="BACKTESTED",
                artifact_uri=None,
                metrics={
                    "precision_class_1": 0.0,
                    "trade_count": 0,
                    "profit_factor": 0.0,
                    "acceptable_walk_forward_windows": 0,
                },
                parameters={},
            )
            session.add(weak)
            session.commit()

            try:
                approve_model(session, settings, model_id="weak-model")
            except ModelApprovalError as exc:
                error = str(exc)

    assert "precision_class_1" in error
    assert "trade_count" in error


def test_model_approval_succeeds_with_valid_artifact_and_metrics(tmp_path) -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_and_features(client)
        settings = get_settings().model_copy(
            update={
                "model_artifact_dir": str(tmp_path),
                "model_training_min_rows": 90,
                "model_holdout_min_rows": 20,
            }
        )
        with client.app.state.db_session_factory() as session:
            model = train_selected_strategy_models(
                session,
                settings,
                trainer=RuleBasedTrainer(),
            )[0]

            approved = approve_model(session, settings, model_id=model.model_id)

    assert approved.status == "APPROVED"
    assert approved.approved_at is not None


def test_model_approval_is_blocked_when_artifact_is_missing_or_corrupt(tmp_path) -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings().model_copy(update={"model_artifact_dir": str(tmp_path)})
        with client.app.state.db_session_factory() as session:
            missing_artifact = valid_backtested_model(
                model_id="missing-artifact",
                artifact_uri=str(tmp_path / "missing.json"),
            )
            session.add(missing_artifact)
            session.commit()

            try:
                approve_model(session, settings, model_id="missing-artifact")
            except ModelApprovalError as exc:
                missing_error = str(exc)

            artifact = tmp_path / "corrupt.json"
            artifact.write_text("not-json", encoding="utf-8")
            artifact.with_suffix(".metadata.json").write_text(
                json.dumps(
                    {
                        "model_id": "corrupt-artifact",
                        "model_role": "entry_confirmation",
                        "strategy_id": "default_rsi_xgboost_long",
                        "strategy_version": "1.0.0",
                        "feature_schema_id": "b3-talib-basic-v1",
                    }
                ),
                encoding="utf-8",
            )
            corrupt_artifact = valid_backtested_model(
                model_id="corrupt-artifact",
                artifact_uri=str(artifact),
            )
            session.add(corrupt_artifact)
            session.commit()

            try:
                approve_model(session, settings, model_id="corrupt-artifact")
            except ModelApprovalError as exc:
                corrupt_error = str(exc)

    assert "model artifact file does not exist" in missing_error
    assert "model artifact file is not valid JSON" in corrupt_error


def valid_backtested_model(*, model_id: str, artifact_uri: str) -> ModelRegistryRecord:
    return ModelRegistryRecord(
        model_id=model_id,
        model_role="entry_confirmation",
        strategy_id="default_rsi_xgboost_long",
        strategy_version="1.0.0",
        asset_symbol="BTC/USDT",
        timeframe="1m",
        feature_schema_id="b3-talib-basic-v1",
        status="BACKTESTED",
        artifact_uri=artifact_uri,
        metrics={
            "precision_class_1": 1.0,
            "trade_count": 1,
            "profit_factor": 2.0,
            "acceptable_walk_forward_windows": 1,
        },
        parameters={},
    )
