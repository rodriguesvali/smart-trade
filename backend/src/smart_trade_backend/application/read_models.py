from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    CommandRequestRecord,
    ModelRegistryRecord,
    OperationalEventRecord,
    PositionRecord,
    SelectedStrategyRecord,
    StrategyRegistryRecord,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import CommandStatus, OperationState, PositionStatus


def split_symbol(symbol: str) -> tuple[str, str]:
    if "/" not in symbol:
        return symbol, ""
    base_asset, quote_asset = symbol.split("/", maxsplit=1)
    return base_asset, quote_asset


def configuration_summary(settings: Settings) -> dict[str, Any]:
    base_asset, quote_asset = split_symbol(settings.symbol)
    return {
        "exchange": settings.exchange,
        "symbol": settings.symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "market_type": "spot",
        "direction": "long_only",
        "timeframe": settings.timeframe,
        "initial_capital_usd": Decimal(str(settings.initial_capital_usd)),
        "mode": settings.mode,
    }


def list_strategies(session: Session) -> list[StrategyRegistryRecord]:
    return list(
        session.scalars(
            select(StrategyRegistryRecord).order_by(
                StrategyRegistryRecord.strategy_id, StrategyRegistryRecord.version
            )
        )
    )


def get_selected_strategy(session: Session) -> SelectedStrategyRecord | None:
    return session.scalars(
        select(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == "SELECTED")
        .order_by(desc(SelectedStrategyRecord.selected_at))
        .limit(1)
    ).first()


def list_models(session: Session) -> list[ModelRegistryRecord]:
    return list(
        session.scalars(select(ModelRegistryRecord).order_by(desc(ModelRegistryRecord.created_at)))
    )


def latest_events(session: Session, limit: int = 50) -> list[OperationalEventRecord]:
    bounded_limit = max(1, min(limit, 200))
    return list(
        session.scalars(
            select(OperationalEventRecord)
            .order_by(desc(OperationalEventRecord.occurred_at))
            .limit(bounded_limit)
        )
    )


def operation_status(session: Session, settings: Settings) -> dict[str, Any]:
    selected_strategy = get_selected_strategy(session)
    approved_models_count = session.scalar(
        select(func.count())
        .select_from(ModelRegistryRecord)
        .where(ModelRegistryRecord.status.in_(["APPROVED", "ACTIVE"]))
    )
    active_models_count = approved_models_count or 0
    if selected_strategy is not None:
        strategy = session.get(StrategyRegistryRecord, selected_strategy.strategy_registry_id)
        required_roles = [
            str(role["role"])
            for role in (strategy.model_roles if strategy is not None else [])
            if "role" in role
        ]
        compatible_models_count = session.scalar(
            select(func.count())
            .select_from(ModelRegistryRecord)
            .where(
                ModelRegistryRecord.status.in_(["APPROVED", "ACTIVE"]),
                ModelRegistryRecord.strategy_id == strategy.strategy_id if strategy else False,
                ModelRegistryRecord.strategy_version == strategy.version if strategy else False,
                ModelRegistryRecord.model_role.in_(required_roles),
                ModelRegistryRecord.asset_symbol == settings.symbol,
                ModelRegistryRecord.timeframe == settings.timeframe,
            )
        )
        active_models_count = compatible_models_count or 0
    open_positions_count = session.scalar(
        select(func.count())
        .select_from(PositionRecord)
        .where(PositionRecord.status == PositionStatus.OPEN.value)
    )
    pending_commands_count = session.scalar(
        select(func.count())
        .select_from(CommandRequestRecord)
        .where(CommandRequestRecord.status == CommandStatus.REQUESTED.value)
    )

    blockers: list[str] = []
    if selected_strategy is None:
        blockers.append("No selected strategy.")
    if not active_models_count:
        blockers.append("No compatible approved or active model for the selected strategy.")

    state = OperationState.IDLE
    if blockers:
        state = OperationState.NOT_READY

    return {
        "state": state.value,
        "mode": settings.mode,
        "exchange": settings.exchange,
        "symbol": settings.symbol,
        "timeframe": settings.timeframe,
        "selected_strategy_id": selected_strategy.strategy_registry_id
        if selected_strategy is not None
        else None,
        "approved_or_active_models": active_models_count or 0,
        "open_positions": open_positions_count or 0,
        "pending_commands": pending_commands_count or 0,
        "blockers": blockers,
    }
