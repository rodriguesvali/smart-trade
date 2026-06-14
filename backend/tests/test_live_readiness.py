import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import (
    EquitySnapshotRecord,
    FeatureSchemaRecord,
    FillRecord,
    ModelRegistryRecord,
    OperationalEventRecord,
    OrderRecord,
    PositionRecord,
    StrategyDecisionRecord,
)
from smart_trade_backend.application.commands import create_command_request
from smart_trade_backend.application.readiness.live import (
    LiveReadinessError,
    enable_live_readiness,
    live_readiness_status,
)
from smart_trade_backend.application.strategy.registry import (
    register_available_strategies,
    select_strategy,
)
from smart_trade_backend.config import get_settings
from smart_trade_backend.db import Base
from smart_trade_backend.domain.enums import CommandType, EventSeverity
from smart_trade_backend.main import app


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def seed_strategy_and_model(client: TestClient) -> None:
    with client.app.state.db_session_factory() as session:
        session.add(
            FeatureSchemaRecord(
                schema_id="b3-talib-basic-v1",
                name="talib_basic",
                version="1.0.0",
                timeframe="1m",
                features=[
                    "rsi_14",
                    "bb_upper_20_2",
                    "bb_middle_20",
                    "bb_lower_20_2",
                    "return_1",
                    "log_return_1",
                    "volume_change_1",
                    "atr_14",
                    "body_pct",
                ],
                parameters={"source": "test"},
            )
        )
        session.commit()
        strategy = register_available_strategies(session)[0]
        select_strategy(session, get_settings(), strategy_registry_id=strategy.id)
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


def seed_paper_evidence(client: TestClient, *, days: int = 7, trades: int = 30) -> None:
    start = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    with client.app.state.db_session_factory() as session:
        for day in range(days):
            session.add(
                EquitySnapshotRecord(
                    asset_symbol="BTC/USDT",
                    equity_usd=Decimal("1000") + Decimal(day),
                    cash_usd=Decimal("1000") + Decimal(day),
                    position_value_usd=Decimal("0"),
                    snapshot_at=start + timedelta(days=day),
                    source="paper",
                )
            )
        model_ref = {
            "model_id": "approved-entry-model",
            "model_role": "entry_confirmation",
            "strategy_id": "default_rsi_xgboost_long",
            "strategy_version": "1.0.0",
            "feature_schema_id": "b3-talib-basic-v1",
            "probability": 0.9,
            "signal": 1,
        }
        position = PositionRecord(
            asset_symbol="BTC/USDT",
            status="CLOSED",
            side="LONG",
            quantity=Decimal("0.01"),
            average_entry_price=Decimal("100"),
            stop_loss_price=Decimal("99"),
            take_profit_price=Decimal("103"),
            opened_at=start,
            closed_at=start + timedelta(minutes=5),
            close_reason="TAKE_PROFIT",
            strategy_id="default_rsi_xgboost_long",
            strategy_version="1.0.0",
            model_refs=[model_ref],
        )
        session.add(position)
        session.flush()
        for index in range(trades):
            decided_at = start + timedelta(minutes=index)
            decision = StrategyDecisionRecord(
                strategy_id="default_rsi_xgboost_long",
                strategy_version="1.0.0",
                asset_symbol="BTC/USDT",
                timeframe="1m",
                action="EXIT_POSITION",
                reason="test paper exit",
                confidence=Decimal("0.9"),
                participating_models=[model_ref],
                risk_updates={},
                decided_at=decided_at,
            )
            session.add(decision)
            session.flush()
            order = OrderRecord(
                client_order_id=f"paper-sell-{index}",
                position_id=position.id,
                decision_id=decision.id,
                asset_symbol="BTC/USDT",
                side="SELL",
                order_type="MARKET",
                status="FILLED",
                requested_quantity=Decimal("0.01"),
                requested_price=Decimal("101"),
                submitted_at=decided_at,
                raw_request={"mode": "paper"},
                raw_response={"mode": "paper", "status": "filled"},
            )
            session.add(order)
            session.flush()
            session.add(
                FillRecord(
                    order_id=order.id,
                    quantity=Decimal("0.01"),
                    price=Decimal("101"),
                    fee_amount=Decimal("0"),
                    fee_asset="USDT",
                    filled_at=decided_at,
                    raw_response={"mode": "paper"},
                )
            )
        session.commit()


def test_live_readiness_blocks_before_seven_paper_days() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_and_model(client)
        seed_paper_evidence(client, days=2, trades=30)
        with client.app.state.db_session_factory() as session:
            status = live_readiness_status(session, get_settings())
            try:
                enable_live_readiness(session, get_settings(), requested_by="operator")
            except LiveReadinessError as exc:
                error = str(exc)

    assert status["ready"] is False
    assert "7 required" in error


def test_live_readiness_blocks_critical_events_and_traceability_failures() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_and_model(client)
        seed_paper_evidence(client)
        with client.app.state.db_session_factory() as session:
            session.add(
                OperationalEventRecord(
                    event_type="runtime_failure",
                    severity=EventSeverity.CRITICAL.value,
                    source="test",
                    message="critical failure",
                    details={},
                    occurred_at=datetime(2026, 6, 8, tzinfo=UTC),
                )
            )
            decision = session.query(StrategyDecisionRecord).first()
            decision.participating_models = [{}]
            session.commit()
            status = live_readiness_status(session, get_settings())

    failures = " ".join(status["failure_reasons"])
    assert status["ready"] is False
    assert "critical operational event" in failures
    assert "missing_model_id" in failures


def test_live_readiness_enablement_is_auditable_when_checks_pass() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_strategy_and_model(client)
        seed_paper_evidence(client)
        with client.app.state.db_session_factory() as session:
            review = enable_live_readiness(session, get_settings(), requested_by="operator")
            command = create_command_request(
                session,
                settings=get_settings(),
                command_type=CommandType.ENABLE_LIVE,
                requested_by="operator",
                payload={},
            )

    assert review.status == "READY"
    assert review.enabled_at is not None
    assert all(check["passed"] for check in review.checks)
    assert command.status == "COMPLETED"
    assert command.result["status"] == "READY"
