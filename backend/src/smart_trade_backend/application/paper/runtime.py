from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    CandleFeatureRecord,
    CandleRecord,
    EquitySnapshotRecord,
    FillRecord,
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


class PaperRuntimeError(ValueError):
    pass


class ProbabilityModel(Protocol):
    def predict_probability(self, values: dict[str, float], feature_names: list[str]) -> float:
        ...


class XGBoostProbabilityModel:
    def __init__(self, artifact_uri: str):
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise PaperRuntimeError(
                "XGBoost is not installed. Run with the backend training dependency group."
            ) from exc
        artifact_path = Path(artifact_uri)
        if not artifact_path.exists():
            raise PaperRuntimeError("Approved model artifact does not exist.")
        self._classifier = XGBClassifier()
        self._classifier.load_model(artifact_path)

    def predict_probability(self, values: dict[str, float], feature_names: list[str]) -> float:
        row = [[values[name] for name in feature_names]]
        probabilities = self._classifier.predict_proba(row)
        return float(probabilities[0][1])


@dataclass(frozen=True)
class PaperRunResult:
    processed_candles: int
    decisions_created: int
    orders_created: int
    fills_created: int
    equity_snapshots_created: int
    open_position_id: int | None


@dataclass(frozen=True)
class RuntimeRow:
    opened_at: datetime
    open_time_ms: int
    close: Decimal
    values: dict[str, float]


def run_paper_replay(
    session: Session,
    settings: Settings,
    *,
    probability_model: ProbabilityModel | None = None,
    limit: int = 500,
) -> PaperRunResult:
    selected, strategy = _selected_strategy(session)
    model = _compatible_model(session, settings, strategy)
    feature_names = list(strategy.required_features)
    predictor = probability_model or XGBoostProbabilityModel(model.artifact_uri or "")
    rows = _runtime_rows(session, settings, model, feature_names, limit=limit)
    last_decision_at = _last_decision_at(session, strategy, settings)
    rows = [row for row in rows if last_decision_at is None or row.opened_at > last_decision_at]

    parameters = {**strategy.default_parameters, **selected.parameters}
    counters = {
        "decisions": 0,
        "orders": 0,
        "fills": 0,
        "equity": 0,
    }
    for row in rows:
        probability = predictor.predict_probability(row.values, feature_names)
        _process_row(
            session,
            settings,
            strategy=strategy,
            parameters=parameters,
            model=model,
            row=row,
            probability=probability,
            counters=counters,
        )

    open_position = _open_position(session, settings)
    return PaperRunResult(
        processed_candles=len(rows),
        decisions_created=counters["decisions"],
        orders_created=counters["orders"],
        fills_created=counters["fills"],
        equity_snapshots_created=counters["equity"],
        open_position_id=open_position.id if open_position else None,
    )


def latest_paper_status(session: Session, settings: Settings) -> dict:
    open_position = _open_position(session, settings)
    latest_equity = session.scalars(
        select(EquitySnapshotRecord)
        .where(EquitySnapshotRecord.asset_symbol == settings.symbol)
        .order_by(desc(EquitySnapshotRecord.snapshot_at))
        .limit(1)
    ).first()
    decisions = list(
        session.scalars(
            select(StrategyDecisionRecord)
            .where(StrategyDecisionRecord.asset_symbol == settings.symbol)
            .order_by(desc(StrategyDecisionRecord.decided_at))
            .limit(20)
        )
    )
    orders = list(
        session.scalars(
            select(OrderRecord)
            .where(OrderRecord.asset_symbol == settings.symbol)
            .order_by(desc(OrderRecord.created_at))
            .limit(20)
        )
    )
    return {
        "open_position": open_position,
        "latest_equity": latest_equity,
        "recent_decisions": decisions,
        "recent_orders": orders,
    }


def _process_row(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    parameters: dict,
    model: ModelRegistryRecord,
    row: RuntimeRow,
    probability: float,
    counters: dict[str, int],
) -> None:
    position = _open_position(session, settings)
    min_probability = float(parameters.get("min_model_probability", 0.5))
    if position is None:
        if (
            row.values.get("rsi_14", 100.0) <= float(parameters.get("oversold_threshold", 30.0))
            and probability >= min_probability
        ):
            _enter_long(
                session,
                settings,
                strategy=strategy,
                parameters=parameters,
                model=model,
                row=row,
                probability=probability,
                counters=counters,
            )
        else:
            _record_hold_decision(
                session,
                settings,
                strategy=strategy,
                model=model,
                row=row,
                probability=probability,
                reason="Entry conditions not met.",
                counters=counters,
            )
        _snapshot_equity(session, settings, row=row, counters=counters)
        return

    _maybe_move_stop(
        session,
        settings,
        strategy=strategy,
        parameters=parameters,
        model=model,
        position=position,
        row=row,
        probability=probability,
        counters=counters,
    )
    exit_reason = _exit_reason(position, row, probability, min_probability)
    if exit_reason:
        _exit_position(
            session,
            settings,
            strategy=strategy,
            model=model,
            position=position,
            row=row,
            probability=probability,
            exit_reason=exit_reason,
            counters=counters,
        )
    else:
        _record_hold_decision(
            session,
            settings,
            strategy=strategy,
            model=model,
            row=row,
            probability=probability,
            reason="Existing paper position remains open.",
            counters=counters,
        )
    _snapshot_equity(session, settings, row=row, counters=counters)


def _enter_long(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    parameters: dict,
    model: ModelRegistryRecord,
    row: RuntimeRow,
    probability: float,
    counters: dict[str, int],
) -> None:
    latest_equity = _latest_equity(session, settings)
    cash = (
        latest_equity.cash_usd
        if latest_equity is not None
        else Decimal(str(settings.initial_capital_usd))
    )
    if cash <= 0:
        _record_hold_decision(
            session,
            settings,
            strategy=strategy,
            model=model,
            row=row,
            probability=probability,
            reason="No cash available for paper entry.",
            counters=counters,
        )
        return

    quantity = cash / row.close
    stop_loss = row.close * (Decimal("1") - Decimal(str(parameters.get("stop_loss_pct", 0.015))))
    take_profit = row.close * (
        Decimal("1") + Decimal(str(parameters.get("take_profit_pct", 0.03)))
    )
    model_refs = [_model_ref(model, probability)]
    decision = _decision(
        session,
        settings,
        strategy=strategy,
        action=DecisionAction.ENTER_LONG,
        reason="RSI/IFR oversold and model confirmation passed.",
        probability=probability,
        model_refs=model_refs,
        row=row,
        risk_updates={
            "stop_loss_price": str(stop_loss),
            "take_profit_price": str(take_profit),
        },
        counters=counters,
    )
    position = PositionRecord(
        asset_symbol=settings.symbol,
        status=PositionStatus.OPEN.value,
        side="LONG",
        quantity=quantity,
        average_entry_price=row.close,
        stop_loss_price=stop_loss,
        take_profit_price=take_profit,
        opened_at=row.opened_at,
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.version,
        model_refs=model_refs,
    )
    session.add(position)
    session.flush()
    order = _filled_order(
        session,
        settings,
        position_id=position.id,
        decision_id=decision.id,
        side="BUY",
        quantity=quantity,
        price=row.close,
        opened_at=row.opened_at,
        raw_request={"mode": "paper", "reason": "entry"},
    )
    _fill(session, order=order, quantity=quantity, price=row.close, filled_at=row.opened_at)
    counters["orders"] += 1
    counters["fills"] += 1
    session.commit()


def _maybe_move_stop(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    parameters: dict,
    model: ModelRegistryRecord,
    position: PositionRecord,
    row: RuntimeRow,
    probability: float,
    counters: dict[str, int],
) -> None:
    entry = position.average_entry_price
    break_even_trigger = Decimal(str(parameters.get("break_even_trigger_pct", 0.012)))
    trailing_stop_pct = Decimal(str(parameters.get("trailing_stop_pct", 0.01)))
    current_stop = position.stop_loss_price or Decimal("0")
    if row.close < entry * (Decimal("1") + break_even_trigger):
        return
    break_even_stop = entry
    trailing_stop = row.close * (Decimal("1") - trailing_stop_pct)
    new_stop = max(current_stop, break_even_stop, trailing_stop)
    if new_stop <= current_stop:
        return
    position.stop_loss_price = new_stop
    _decision(
        session,
        settings,
        strategy=strategy,
        action=DecisionAction.MOVE_STOP,
        reason="Paper runtime moved long stop after break-even/trailing condition.",
        probability=probability,
        model_refs=[_model_ref(model, probability)],
        row=row,
        risk_updates={"stop_loss_price": str(new_stop)},
        counters=counters,
    )
    session.commit()


def _exit_position(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    model: ModelRegistryRecord,
    position: PositionRecord,
    row: RuntimeRow,
    probability: float,
    exit_reason: str,
    counters: dict[str, int],
) -> None:
    model_refs = [_model_ref(model, probability)]
    decision = _decision(
        session,
        settings,
        strategy=strategy,
        action=DecisionAction.EXIT_POSITION,
        reason=exit_reason,
        probability=probability,
        model_refs=model_refs,
        row=row,
        risk_updates={"exit_reason": exit_reason},
        counters=counters,
    )
    order = _filled_order(
        session,
        settings,
        position_id=position.id,
        decision_id=decision.id,
        side="SELL",
        quantity=position.quantity,
        price=row.close,
        opened_at=row.opened_at,
        raw_request={"mode": "paper", "reason": exit_reason},
    )
    _fill(
        session,
        order=order,
        quantity=position.quantity,
        price=row.close,
        filled_at=row.opened_at,
    )
    position.status = PositionStatus.CLOSED.value
    position.closed_at = row.opened_at
    position.close_reason = exit_reason
    counters["orders"] += 1
    counters["fills"] += 1
    session.commit()


def _record_hold_decision(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    model: ModelRegistryRecord,
    row: RuntimeRow,
    probability: float,
    reason: str,
    counters: dict[str, int],
) -> None:
    _decision(
        session,
        settings,
        strategy=strategy,
        action=DecisionAction.HOLD,
        reason=reason,
        probability=probability,
        model_refs=[_model_ref(model, probability)],
        row=row,
        risk_updates={},
        counters=counters,
    )
    session.commit()


def _decision(
    session: Session,
    settings: Settings,
    *,
    strategy: StrategyRegistryRecord,
    action: DecisionAction,
    reason: str,
    probability: float,
    model_refs: list[dict],
    row: RuntimeRow,
    risk_updates: dict,
    counters: dict[str, int],
) -> StrategyDecisionRecord:
    decision = StrategyDecisionRecord(
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.version,
        asset_symbol=settings.symbol,
        timeframe=settings.timeframe,
        action=action.value,
        reason=reason,
        confidence=Decimal(str(round(probability, 8))),
        participating_models=model_refs,
        risk_updates={"open_time_ms": row.open_time_ms, **risk_updates},
        decided_at=row.opened_at,
    )
    session.add(decision)
    session.flush()
    counters["decisions"] += 1
    return decision


def _filled_order(
    session: Session,
    settings: Settings,
    *,
    position_id: int,
    decision_id: int,
    side: str,
    quantity: Decimal,
    price: Decimal,
    opened_at: datetime,
    raw_request: dict,
) -> OrderRecord:
    order = OrderRecord(
        client_order_id=f"paper-{side.lower()}-{position_id}-{int(opened_at.timestamp() * 1000)}",
        exchange_order_id=None,
        position_id=position_id,
        decision_id=decision_id,
        asset_symbol=settings.symbol,
        side=side,
        order_type="MARKET",
        status=OrderStatus.FILLED.value,
        requested_quantity=quantity,
        requested_price=price,
        submitted_at=opened_at,
        raw_request=raw_request,
        raw_response={"mode": "paper", "status": "filled"},
    )
    session.add(order)
    session.flush()
    return order


def _fill(
    session: Session,
    *,
    order: OrderRecord,
    quantity: Decimal,
    price: Decimal,
    filled_at: datetime,
) -> None:
    session.add(
        FillRecord(
            order_id=order.id,
            exchange_fill_id=None,
            quantity=quantity,
            price=price,
            fee_amount=Decimal("0"),
            fee_asset="USDT",
            filled_at=filled_at,
            raw_response={"mode": "paper"},
        )
    )


def _snapshot_equity(
    session: Session, settings: Settings, *, row: RuntimeRow, counters: dict[str, int]
) -> None:
    position = _open_position(session, settings)
    if position is None:
        latest = _latest_equity(session, settings)
        equity = (
            latest.equity_usd
            if latest is not None
            else Decimal(str(settings.initial_capital_usd))
        )
        cash = equity
        position_value = Decimal("0")
    else:
        position_value = position.quantity * row.close
        cash = Decimal("0")
        equity = position_value
    session.add(
        EquitySnapshotRecord(
            asset_symbol=settings.symbol,
            equity_usd=equity,
            cash_usd=cash,
            position_value_usd=position_value,
            snapshot_at=row.opened_at,
            source="paper",
        )
    )
    counters["equity"] += 1
    session.commit()


def _exit_reason(
    position: PositionRecord,
    row: RuntimeRow,
    probability: float,
    min_probability: float,
) -> str:
    if position.stop_loss_price is not None and row.close <= position.stop_loss_price:
        return "STOP_LOSS"
    if position.take_profit_price is not None and row.close >= position.take_profit_price:
        return "TAKE_PROFIT"
    if probability < min_probability and row.close > position.average_entry_price:
        return "MODEL_CONFIRMATION_LOST"
    return ""


def _selected_strategy(session: Session) -> tuple[SelectedStrategyRecord, StrategyRegistryRecord]:
    selected = session.scalars(
        select(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == StrategyStatus.SELECTED.value)
        .order_by(desc(SelectedStrategyRecord.selected_at))
        .limit(1)
    ).first()
    if selected is None:
        raise PaperRuntimeError("No selected strategy.")
    strategy = session.get(StrategyRegistryRecord, selected.strategy_registry_id)
    if strategy is None:
        raise PaperRuntimeError("Selected strategy registry record is missing.")
    return selected, strategy


def _compatible_model(
    session: Session, settings: Settings, strategy: StrategyRegistryRecord
) -> ModelRegistryRecord:
    required_roles = [str(role["role"]) for role in strategy.model_roles if "role" in role]
    if not required_roles:
        raise PaperRuntimeError("Selected strategy does not declare model roles.")
    model = session.scalars(
        select(ModelRegistryRecord)
        .where(
            ModelRegistryRecord.status.in_([ModelStatus.APPROVED.value, ModelStatus.ACTIVE.value]),
            ModelRegistryRecord.strategy_id == strategy.strategy_id,
            ModelRegistryRecord.strategy_version == strategy.version,
            ModelRegistryRecord.model_role == required_roles[0],
            ModelRegistryRecord.asset_symbol == settings.symbol,
            ModelRegistryRecord.timeframe == settings.timeframe,
        )
        .order_by(desc(ModelRegistryRecord.approved_at), desc(ModelRegistryRecord.created_at))
        .limit(1)
    ).first()
    if model is None:
        raise PaperRuntimeError("No compatible approved or active model for selected strategy.")
    return model


def _runtime_rows(
    session: Session,
    settings: Settings,
    model: ModelRegistryRecord,
    feature_names: list[str],
    *,
    limit: int,
) -> list[RuntimeRow]:
    candles = list(
        session.scalars(
            select(CandleRecord)
            .where(
                CandleRecord.exchange == settings.exchange,
                CandleRecord.symbol == settings.symbol,
                CandleRecord.timeframe == settings.timeframe,
            )
            .order_by(CandleRecord.open_time_ms)
        )
    )
    candle_by_time = {candle.open_time_ms: candle for candle in candles}
    features = list(
        session.scalars(
            select(CandleFeatureRecord)
            .where(
                CandleFeatureRecord.exchange == settings.exchange,
                CandleFeatureRecord.symbol == settings.symbol,
                CandleFeatureRecord.timeframe == settings.timeframe,
                CandleFeatureRecord.feature_schema_id == model.feature_schema_id,
            )
            .order_by(CandleFeatureRecord.open_time_ms)
            .limit(max(1, min(limit, 5000)))
        )
    )
    rows: list[RuntimeRow] = []
    for feature in features:
        candle = candle_by_time.get(feature.open_time_ms)
        if candle is None:
            continue
        try:
            values = {name: float(feature.values[name]) for name in feature_names}
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(
            RuntimeRow(
                opened_at=feature.candle_opened_at,
                open_time_ms=feature.open_time_ms,
                close=candle.close,
                values=values,
            )
        )
    return rows


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


def _latest_equity(session: Session, settings: Settings) -> EquitySnapshotRecord | None:
    return session.scalars(
        select(EquitySnapshotRecord)
        .where(EquitySnapshotRecord.asset_symbol == settings.symbol)
        .order_by(desc(EquitySnapshotRecord.snapshot_at))
        .limit(1)
    ).first()


def _last_decision_at(
    session: Session, strategy: StrategyRegistryRecord, settings: Settings
) -> datetime | None:
    decision = session.scalars(
        select(StrategyDecisionRecord)
        .where(
            StrategyDecisionRecord.strategy_id == strategy.strategy_id,
            StrategyDecisionRecord.strategy_version == strategy.version,
            StrategyDecisionRecord.asset_symbol == settings.symbol,
            StrategyDecisionRecord.timeframe == settings.timeframe,
        )
        .order_by(desc(StrategyDecisionRecord.decided_at))
        .limit(1)
    ).first()
    return decision.decided_at if decision is not None else None


def _model_ref(model: ModelRegistryRecord, probability: float) -> dict:
    return {
        "model_id": model.model_id,
        "model_role": model.model_role,
        "strategy_id": model.strategy_id,
        "strategy_version": model.strategy_version,
        "feature_schema_id": model.feature_schema_id,
        "probability": probability,
        "signal": 1 if probability >= 0.5 else 0,
    }
