from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    FillRecord,
    LiveReadinessReviewRecord,
    ModelRegistryRecord,
    OrderRecord,
    PositionRecord,
    SelectedStrategyRecord,
    StrategyDecisionRecord,
    StrategyRegistryRecord,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import (
    DecisionAction,
    ModelStatus,
    OrderStatus,
    PositionStatus,
    StrategyStatus,
)

LIVE_ACK_PHRASE = "I_UNDERSTAND_LIVE_RISK"
TERMINAL_ORDER_STATUSES = {
    OrderStatus.FILLED.value,
    OrderStatus.CANCELED.value,
    OrderStatus.REJECTED.value,
    OrderStatus.FAILED.value,
}


class LiveExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class ExchangeMarketRules:
    symbol: str
    base: str
    quote: str
    spot: bool
    active: bool
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    min_cost: Decimal | None = None
    max_cost: Decimal | None = None
    amount_precision: int | None = None
    price_precision: int | None = None
    taker_fee_rate: Decimal | None = None


@dataclass(frozen=True)
class ExchangeOrderResult:
    exchange_order_id: str | None
    status: str
    filled_quantity: Decimal
    average_price: Decimal | None
    fee_amount: Decimal | None
    fee_asset: str | None
    raw_response: dict[str, Any]


class SpotExchangePort(Protocol):
    def validate_market(self, symbol: str) -> ExchangeMarketRules:
        ...

    def fetch_balance(self) -> dict[str, Decimal]:
        ...

    def create_market_buy_order(
        self, *, symbol: str, quote_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        ...

    def create_market_sell_order(
        self, *, symbol: str, base_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        ...


@dataclass(frozen=True)
class LiveExecutionResult:
    order: OrderRecord
    duplicate: bool = False


def latest_live_status(session: Session, settings: Settings) -> dict[str, Any]:
    latest_review = _latest_enabled_readiness_review(session)
    return {
        "live_enabled_by_config": _config_live_enabled(settings),
        "manual_readiness_enabled": latest_review is not None,
        "pending_order_count": _pending_live_order_count(session),
        "open_position": _open_position(session, settings),
        "recent_orders": _recent_live_orders(session, settings),
        "latest_readiness_review": latest_review,
    }


def execute_live_order(
    session: Session,
    settings: Settings,
    *,
    side: Literal["BUY", "SELL"],
    idempotency_key: str,
    requested_by: str,
    quote_amount_usd: Decimal | None = None,
    exchange: SpotExchangePort | None = None,
) -> LiveExecutionResult:
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise LiveExecutionError("Live execution side must be BUY or SELL.")
    client_order_id = _client_order_id(side, idempotency_key)
    existing_order = _order_by_client_id(session, client_order_id)
    if existing_order is not None:
        return LiveExecutionResult(order=existing_order, duplicate=True)

    _assert_config_gates(settings)
    _assert_credentials(settings)
    _assert_manual_readiness(session)
    _, strategy = _selected_strategy(session)
    model_refs = _compatible_model_refs(session, settings, strategy)
    if not model_refs:
        raise LiveExecutionError(
            "No compatible approved or active model is available for live execution."
        )
    _assert_no_unreconciled_live_orders(session)

    amount = quote_amount_usd or Decimal(str(settings.live_order_quote_amount_usd))
    if amount <= 0:
        raise LiveExecutionError("Live quote amount must be positive.")
    max_quote_amount = Decimal(str(settings.live_max_order_quote_amount_usd))
    if amount > max_quote_amount:
        raise LiveExecutionError("Live quote amount exceeds configured maximum.")

    open_position = _open_position(session, settings)
    if side == "BUY" and open_position is not None:
        raise LiveExecutionError("Live BUY blocked because an open position already exists.")
    if side == "SELL" and open_position is None:
        raise LiveExecutionError("Live SELL blocked because there is no open position.")

    if exchange is None:
        exchange = _private_exchange_adapter(settings)
    market = exchange.validate_market(settings.symbol)
    _assert_market_rules(settings, market, side=side, quote_amount=amount, position=open_position)
    balance = exchange.fetch_balance()
    _assert_balance(
        settings,
        market,
        balance,
        side=side,
        quote_amount=amount,
        position=open_position,
    )

    decision = StrategyDecisionRecord(
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.version,
        asset_symbol=settings.symbol,
        timeframe=settings.timeframe,
        action=DecisionAction.ENTER_LONG.value
        if side == "BUY"
        else DecisionAction.EXIT_POSITION.value,
        reason=f"live {side.lower()} authorized by readiness gate",
        confidence=None,
        participating_models=model_refs,
        risk_updates={
            "mode": "live",
            "requested_by": requested_by,
            "idempotency_key": idempotency_key,
        },
        decided_at=datetime.now(UTC),
    )
    session.add(decision)
    session.flush()

    requested_quantity = amount if side == "BUY" else Decimal(str(open_position.quantity))
    order = OrderRecord(
        client_order_id=client_order_id,
        exchange_order_id=None,
        position_id=open_position.id if open_position is not None else None,
        decision_id=decision.id,
        asset_symbol=settings.symbol,
        side=side,
        order_type="MARKET",
        status=OrderStatus.REQUESTED.value,
        requested_quantity=requested_quantity,
        requested_price=None,
        submitted_at=None,
        raw_request={
            "mode": "live",
            "side": side,
            "symbol": settings.symbol,
            "client_order_id": client_order_id,
            "idempotency_key": idempotency_key,
            "requested_by": requested_by,
            "requested_quantity_unit": "quote" if side == "BUY" else "base",
        },
        raw_response={},
    )
    session.add(order)
    session.flush()

    try:
        response = (
            exchange.create_market_buy_order(
                symbol=settings.symbol,
                quote_amount=amount,
                client_order_id=client_order_id,
            )
            if side == "BUY"
            else exchange.create_market_sell_order(
                symbol=settings.symbol,
                base_amount=Decimal(str(open_position.quantity)),
                client_order_id=client_order_id,
            )
        )
    except Exception as exc:
        order.status = OrderStatus.FAILED.value
        order.raw_response = {
            "error_type": exc.__class__.__name__,
            "message": _safe_error_message(str(exc)),
        }
        session.commit()
        session.refresh(order)
        raise LiveExecutionError("Live exchange order submission failed safely.") from exc

    normalized_status = _order_status_from_exchange(response)
    if (
        normalized_status == OrderStatus.FILLED.value
        and (response.filled_quantity <= 0 or response.average_price is None)
    ) or (response.filled_quantity > 0 and response.average_price is None):
        order.exchange_order_id = response.exchange_order_id
        order.status = OrderStatus.SUBMITTED.value
        order.submitted_at = datetime.now(UTC)
        order.raw_response = {
            **response.raw_response,
            "reconciliation_required": True,
            "validation_error": "filled live response missing quantity or average price",
        }
        session.commit()
        session.refresh(order)
        raise LiveExecutionError(
            "Live exchange response requires reconciliation before continuing."
        )

    order.exchange_order_id = response.exchange_order_id
    order.status = normalized_status
    order.submitted_at = datetime.now(UTC)
    order.raw_response = response.raw_response

    if response.filled_quantity > 0 and response.average_price is not None:
        session.add(
            FillRecord(
                order_id=order.id,
                exchange_fill_id=response.exchange_order_id,
                quantity=response.filled_quantity,
                price=response.average_price,
                fee_amount=response.fee_amount,
                fee_asset=response.fee_asset,
                filled_at=order.submitted_at,
                raw_response=response.raw_response,
            )
        )
        if side == "BUY":
            position = PositionRecord(
                asset_symbol=settings.symbol,
                status=PositionStatus.OPEN.value,
                side="LONG",
                quantity=response.filled_quantity,
                average_entry_price=response.average_price,
                stop_loss_price=None,
                take_profit_price=None,
                opened_at=order.submitted_at,
                closed_at=None,
                close_reason=None,
                strategy_id=strategy.strategy_id,
                strategy_version=strategy.version,
                model_refs=model_refs,
            )
            session.add(position)
            session.flush()
            order.position_id = position.id
        else:
            open_position.status = PositionStatus.CLOSED.value
            open_position.closed_at = order.submitted_at
            open_position.close_reason = "LIVE_EXIT"

    session.commit()
    session.refresh(order)
    return LiveExecutionResult(order=order)


def _private_exchange_adapter(settings: Settings) -> SpotExchangePort:
    from smart_trade_backend.adapters.exchange.ccxt_private import (
        CcxtPrivateSpotExchangeAdapter,
    )

    return CcxtPrivateSpotExchangeAdapter(settings=settings)


def _config_live_enabled(settings: Settings) -> bool:
    return (
        settings.allow_live_trading
        and settings.live_trading_ack == LIVE_ACK_PHRASE
        and bool(settings.exchange_api_key)
        and bool(settings.exchange_api_secret)
    )


def _assert_config_gates(settings: Settings) -> None:
    if not settings.allow_live_trading:
        raise LiveExecutionError("Live trading is disabled by configuration.")
    if settings.live_trading_ack != LIVE_ACK_PHRASE:
        raise LiveExecutionError("Live trading acknowledgement is missing or invalid.")


def _assert_credentials(settings: Settings) -> None:
    if not settings.exchange_api_key or not settings.exchange_api_secret:
        raise LiveExecutionError("Live exchange credentials are not configured.")


def _assert_manual_readiness(session: Session) -> None:
    if _latest_enabled_readiness_review(session) is None:
        raise LiveExecutionError("Live readiness has not been manually enabled.")


def _latest_enabled_readiness_review(session: Session) -> LiveReadinessReviewRecord | None:
    return session.scalars(
        select(LiveReadinessReviewRecord)
        .where(
            LiveReadinessReviewRecord.status == "READY",
            LiveReadinessReviewRecord.enabled_at.is_not(None),
        )
        .order_by(desc(LiveReadinessReviewRecord.enabled_at))
        .limit(1)
    ).first()


def _selected_strategy(session: Session) -> tuple[SelectedStrategyRecord, StrategyRegistryRecord]:
    selected = session.scalars(
        select(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == StrategyStatus.SELECTED.value)
        .order_by(desc(SelectedStrategyRecord.selected_at))
        .limit(1)
    ).first()
    if selected is None:
        raise LiveExecutionError("No selected strategy is available for live execution.")
    strategy = session.get(StrategyRegistryRecord, selected.strategy_registry_id)
    if strategy is None:
        raise LiveExecutionError("Selected strategy registry record is missing.")
    return selected, strategy


def _compatible_model_refs(
    session: Session, settings: Settings, strategy: StrategyRegistryRecord
) -> list[dict[str, Any]]:
    roles = [str(role["role"]) for role in strategy.model_roles if "role" in role]
    if not roles:
        return []
    models = list(
        session.scalars(
            select(ModelRegistryRecord)
            .where(
                ModelRegistryRecord.status.in_(
                    [ModelStatus.APPROVED.value, ModelStatus.ACTIVE.value]
                ),
                ModelRegistryRecord.strategy_id == strategy.strategy_id,
                ModelRegistryRecord.strategy_version == strategy.version,
                ModelRegistryRecord.model_role.in_(roles),
                ModelRegistryRecord.asset_symbol == settings.symbol,
                ModelRegistryRecord.timeframe == settings.timeframe,
            )
            .order_by(desc(ModelRegistryRecord.approved_at), desc(ModelRegistryRecord.created_at))
        )
    )
    return [
        {
            "model_id": model.model_id,
            "model_role": model.model_role,
            "strategy_id": model.strategy_id,
            "strategy_version": model.strategy_version,
            "feature_schema_id": model.feature_schema_id,
            "status": model.status,
        }
        for model in models
    ]


def _assert_no_unreconciled_live_orders(session: Session) -> None:
    if _pending_live_order_count(session) > 0:
        raise LiveExecutionError(
            "Unreconciled live order exists; reconcile before submitting another order."
        )


def _pending_live_order_count(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(OrderRecord)
            .where(OrderRecord.raw_request["mode"].as_string() == "live")
            .where(OrderRecord.status.not_in(TERMINAL_ORDER_STATUSES))
        )
        or 0
    )


def _assert_market_rules(
    settings: Settings,
    market: ExchangeMarketRules,
    *,
    side: str,
    quote_amount: Decimal,
    position: PositionRecord | None,
) -> None:
    if not market.spot or not market.active:
        raise LiveExecutionError("Exchange market is not active spot.")
    if market.symbol != settings.symbol:
        raise LiveExecutionError("Exchange market symbol does not match configured symbol.")
    max_fee = Decimal(str(settings.live_max_fee_rate))
    if market.taker_fee_rate is None or market.taker_fee_rate > max_fee:
        raise LiveExecutionError(
            "Exchange taker fee rate is unavailable or exceeds the live limit."
        )
    if side == "BUY":
        if market.min_cost is not None and quote_amount < market.min_cost:
            raise LiveExecutionError("Live BUY quote amount is below exchange minimum cost.")
        if market.max_cost is not None and quote_amount > market.max_cost:
            raise LiveExecutionError("Live BUY quote amount exceeds exchange maximum cost.")
    elif position is not None:
        base_amount = Decimal(str(position.quantity))
        if market.min_amount is not None and base_amount < market.min_amount:
            raise LiveExecutionError("Live SELL quantity is below exchange minimum amount.")
        if market.max_amount is not None and base_amount > market.max_amount:
            raise LiveExecutionError("Live SELL quantity exceeds exchange maximum amount.")


def _assert_balance(
    settings: Settings,
    market: ExchangeMarketRules,
    balance: dict[str, Decimal],
    *,
    side: str,
    quote_amount: Decimal,
    position: PositionRecord | None,
) -> None:
    if side == "BUY":
        available = balance.get(market.quote, Decimal("0"))
        if available < quote_amount:
            raise LiveExecutionError("Insufficient quote balance for live BUY.")
        return
    if position is None:
        raise LiveExecutionError("Live SELL blocked because there is no open position.")
    available = balance.get(market.base, Decimal("0"))
    base_amount = Decimal(str(position.quantity))
    if available < base_amount:
        raise LiveExecutionError("Insufficient base balance for live SELL.")


def _order_status_from_exchange(response: ExchangeOrderResult) -> str:
    status = response.status.lower()
    if status in {"closed", "filled"}:
        return OrderStatus.FILLED.value
    if status in {"canceled", "cancelled"}:
        return OrderStatus.CANCELED.value
    if status in {"rejected"}:
        return OrderStatus.REJECTED.value
    if response.filled_quantity > 0:
        return OrderStatus.PARTIALLY_FILLED.value
    return OrderStatus.SUBMITTED.value


def _open_position(session: Session, settings: Settings) -> PositionRecord | None:
    return session.scalars(
        select(PositionRecord)
        .where(
            PositionRecord.asset_symbol == settings.symbol,
            PositionRecord.status == PositionStatus.OPEN.value,
        )
        .order_by(desc(PositionRecord.opened_at))
        .limit(1)
    ).first()


def _recent_live_orders(session: Session, settings: Settings, limit: int = 10) -> list[OrderRecord]:
    return list(
        session.scalars(
            select(OrderRecord)
            .where(
                OrderRecord.asset_symbol == settings.symbol,
                OrderRecord.raw_request["mode"].as_string() == "live",
            )
            .order_by(desc(OrderRecord.created_at))
            .limit(limit)
        )
    )


def _order_by_client_id(session: Session, client_order_id: str) -> OrderRecord | None:
    return session.scalars(
        select(OrderRecord).where(OrderRecord.client_order_id == client_order_id).limit(1)
    ).first()


def _client_order_id(side: str, idempotency_key: str) -> str:
    key = idempotency_key.strip()
    if not key:
        raise LiveExecutionError("Live idempotency key is required.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
        raise LiveExecutionError("Live idempotency key must use only letters, numbers, '-' or '_'.")
    return f"st-live-{side.lower()}-{key}"[:128]


def _safe_error_message(message: str) -> str:
    redacted = re.sub(r"(?i)(api[_ -]?key|secret|password|token)[^,;\\s]*", "[redacted]", message)
    return redacted[:500]
