import os
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import (
    FeatureSchemaRecord,
    FillRecord,
    LiveReadinessReviewRecord,
    ModelRegistryRecord,
    OrderRecord,
    PositionRecord,
)
from smart_trade_backend.application.live.execution import (
    LIVE_ACK_PHRASE,
    ExchangeMarketRules,
    ExchangeOrderResult,
    LiveExecutionError,
    execute_live_order,
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


class FakeSpotExchange:
    def __init__(
        self,
        *,
        min_cost: Decimal = Decimal("10"),
        quote_balance: Decimal = Decimal("1000"),
        base_balance: Decimal = Decimal("1"),
        fail_submission: bool = False,
    ):
        self.min_cost = min_cost
        self.quote_balance = quote_balance
        self.base_balance = base_balance
        self.fail_submission = fail_submission
        self.calls: list[dict[str, object]] = []

    def validate_market(self, symbol: str) -> ExchangeMarketRules:
        return ExchangeMarketRules(
            symbol=symbol,
            base="BTC",
            quote="USDT",
            spot=True,
            active=True,
            min_amount=Decimal("0.0001"),
            min_cost=self.min_cost,
            taker_fee_rate=Decimal("0.001"),
        )

    def fetch_balance(self) -> dict[str, Decimal]:
        return {"USDT": self.quote_balance, "BTC": self.base_balance}

    def create_market_buy_order(
        self, *, symbol: str, quote_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        self.calls.append({"side": "BUY", "symbol": symbol, "client_order_id": client_order_id})
        if self.fail_submission:
            raise RuntimeError("timeout apiKey=public secret=super-secret")
        return ExchangeOrderResult(
            exchange_order_id="bybit-buy-1",
            status="closed",
            filled_quantity=Decimal("0.001"),
            average_price=Decimal("25000"),
            fee_amount=Decimal("0.01"),
            fee_asset="USDT",
            raw_response={"id": "bybit-buy-1", "status": "closed", "filled": "0.001"},
        )

    def create_market_sell_order(
        self, *, symbol: str, base_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        self.calls.append(
            {
                "side": "SELL",
                "symbol": symbol,
                "client_order_id": client_order_id,
                "base_amount": base_amount,
            }
        )
        return ExchangeOrderResult(
            exchange_order_id="bybit-sell-1",
            status="closed",
            filled_quantity=base_amount,
            average_price=Decimal("26000"),
            fee_amount=Decimal("0.01"),
            fee_asset="USDT",
            raw_response={"id": "bybit-sell-1", "status": "closed", "filled": str(base_amount)},
        )


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def live_settings(**overrides):
    return get_settings().model_copy(
        update={
            "allow_live_trading": True,
            "live_trading_ack": LIVE_ACK_PHRASE,
            "exchange_api_key": "public",
            "exchange_api_secret": "super-secret",
            "live_order_quote_amount_usd": 25.0,
            "live_max_order_quote_amount_usd": 100.0,
            "live_max_fee_rate": 0.005,
            **overrides,
        }
    )


def seed_live_prerequisites(client: TestClient) -> None:
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
        strategy = register_available_strategies(session)[0]
        select_strategy(session, live_settings(), strategy_registry_id=strategy.id)
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
        session.add(
            LiveReadinessReviewRecord(
                status="READY",
                requested_by="qa",
                reviewed_at=datetime(2026, 6, 14, tzinfo=UTC),
                enabled_at=datetime(2026, 6, 14, tzinfo=UTC),
                checks=[{"check_id": "test", "passed": True}],
                evidence={"source": "test"},
                failure_reasons=[],
            )
        )
        session.commit()


def test_live_execution_blocks_missing_credentials_without_secret_exposure() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            try:
                execute_live_order(
                    session,
                    live_settings(exchange_api_secret=None),
                    side="BUY",
                    idempotency_key="missing_creds",
                    requested_by="qa",
                    exchange=FakeSpotExchange(),
                )
            except LiveExecutionError as exc:
                error = str(exc)

    assert "credentials" in error
    assert "super-secret" not in error


def test_live_execution_validates_exchange_limits_before_private_order() -> None:
    exchange = FakeSpotExchange(min_cost=Decimal("50"))
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            try:
                execute_live_order(
                    session,
                    live_settings(),
                    side="BUY",
                    idempotency_key="limit_block",
                    requested_by="qa",
                    exchange=exchange,
                )
            except LiveExecutionError as exc:
                error = str(exc)

    assert "minimum cost" in error
    assert exchange.calls == []


def test_live_execution_authorized_buy_persists_order_fill_and_position() -> None:
    exchange = FakeSpotExchange()
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            result = execute_live_order(
                session,
                live_settings(),
                side="BUY",
                idempotency_key="buy_1",
                requested_by="qa",
                exchange=exchange,
            )
            order_count = session.query(OrderRecord).count()
            fill_count = session.query(FillRecord).count()
            position = session.query(PositionRecord).one()

    assert result.order.status == "FILLED"
    assert order_count == 1
    assert fill_count == 1
    assert position.status == "OPEN"
    assert position.quantity == Decimal("0.001")
    assert exchange.calls == [
        {"side": "BUY", "symbol": "BTC/USDT", "client_order_id": "st-live-buy-buy_1"}
    ]


def test_live_execution_authorized_sell_closes_open_position() -> None:
    exchange = FakeSpotExchange()
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            execute_live_order(
                session,
                live_settings(),
                side="BUY",
                idempotency_key="sell_setup",
                requested_by="qa",
                exchange=exchange,
            )
            result = execute_live_order(
                session,
                live_settings(),
                side="SELL",
                idempotency_key="sell_1",
                requested_by="qa",
                exchange=exchange,
            )
            position = session.query(PositionRecord).one()
            order_count = session.query(OrderRecord).count()
            fill_count = session.query(FillRecord).count()

    assert result.order.side == "SELL"
    assert result.order.status == "FILLED"
    assert position.status == "CLOSED"
    assert position.close_reason == "LIVE_EXIT"
    assert order_count == 2
    assert fill_count == 2
    assert exchange.calls[-1]["side"] == "SELL"


def test_live_execution_exchange_error_preserves_consistent_state() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            try:
                execute_live_order(
                    session,
                    live_settings(),
                    side="BUY",
                    idempotency_key="timeout_1",
                    requested_by="qa",
                    exchange=FakeSpotExchange(fail_submission=True),
                )
            except LiveExecutionError as exc:
                error = str(exc)
            order = session.query(OrderRecord).one()
            fill_count = session.query(FillRecord).count()
            position_count = session.query(PositionRecord).count()

    assert "failed safely" in error
    assert order.status == "FAILED"
    assert "super-secret" not in str(order.raw_response)
    assert fill_count == 0
    assert position_count == 0


def test_live_execution_idempotency_prevents_duplicate_order_submission() -> None:
    exchange = FakeSpotExchange()
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            first = execute_live_order(
                session,
                live_settings(),
                side="BUY",
                idempotency_key="same_key",
                requested_by="qa",
                exchange=exchange,
            )
            second = execute_live_order(
                session,
                live_settings(),
                side="BUY",
                idempotency_key="same_key",
                requested_by="qa",
                exchange=exchange,
            )
            order_count = session.query(OrderRecord).count()

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.order.id == first.order.id
    assert order_count == 1
    assert len(exchange.calls) == 1


def test_live_execution_blocks_new_order_when_pending_live_order_needs_reconciliation() -> None:
    exchange = FakeSpotExchange()
    with TestClient(app) as client:
        prepare_schema(client)
        seed_live_prerequisites(client)
        with client.app.state.db_session_factory() as session:
            session.add(
                OrderRecord(
                    client_order_id="st-live-buy-pending",
                    asset_symbol="BTC/USDT",
                    side="BUY",
                    order_type="MARKET",
                    status="SUBMITTED",
                    requested_quantity=Decimal("25"),
                    requested_price=None,
                    submitted_at=datetime(2026, 6, 14, tzinfo=UTC),
                    raw_request={"mode": "live"},
                    raw_response={"id": "pending"},
                )
            )
            session.commit()
            try:
                execute_live_order(
                    session,
                    live_settings(),
                    side="BUY",
                    idempotency_key="new_key",
                    requested_by="qa",
                    exchange=exchange,
                )
            except LiveExecutionError as exc:
                error = str(exc)

    assert "Unreconciled live order" in error
    assert exchange.calls == []
