from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from smart_trade_backend.domain.enums import (
    CommandStatus,
    CommandType,
    EventSeverity,
    MarketType,
    ModelStatus,
    OperationMode,
    TradeDirection,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AssetConfiguration:
    symbol: str
    base_asset: str
    quote_asset: str
    exchange: str
    timeframe: str
    initial_capital_usd: Decimal
    market_type: MarketType = MarketType.SPOT
    direction: TradeDirection = TradeDirection.LONG_ONLY
    mode: OperationMode = OperationMode.PAPER


@dataclass(frozen=True)
class ModelRoleRequirement:
    role: str
    output_contract: str = "binary"
    required_statuses: tuple[ModelStatus, ...] = (ModelStatus.APPROVED, ModelStatus.ACTIVE)


@dataclass(frozen=True)
class StrategyRegistration:
    strategy_id: str
    version: str
    name: str
    description: str
    supported_market: MarketType
    supported_direction: TradeDirection
    timeframes: tuple[str, ...]
    parameter_schema: dict[str, Any]
    default_parameters: dict[str, Any]
    required_features: tuple[str, ...]
    model_roles: tuple[ModelRoleRequirement, ...]


@dataclass(frozen=True)
class ModelRegistryEntry:
    model_id: str
    model_role: str
    strategy_id: str
    strategy_version: str
    asset_symbol: str
    timeframe: str
    feature_schema_id: str
    status: ModelStatus
    artifact_uri: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandRequest:
    command_type: CommandType
    requested_by: str
    payload: dict[str, Any]
    status: CommandStatus = CommandStatus.REQUESTED
    requested_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class OperationalEvent:
    event_type: str
    severity: EventSeverity
    message: str
    source: str
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)

