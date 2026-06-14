from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from smart_trade_backend.domain.enums import CommandType


class ConfigurationSummary(BaseModel):
    exchange: str
    symbol: str
    base_asset: str
    quote_asset: str
    market_type: str
    direction: str
    timeframe: str
    initial_capital_usd: Decimal
    mode: str


class StrategySummary(BaseModel):
    id: int
    strategy_id: str
    version: str
    name: str
    description: str
    status: str
    supported_market: str
    supported_direction: str
    timeframes: list[str]
    required_features: list[str]
    model_roles: list[dict[str, Any]]
    default_parameters: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class StrategiesResponse(BaseModel):
    selected_strategy_id: int | None
    items: list[StrategySummary]


class ModelSummary(BaseModel):
    id: int
    model_id: str
    model_role: str
    strategy_id: str
    strategy_version: str
    asset_symbol: str
    timeframe: str
    feature_schema_id: str
    status: str
    artifact_uri: str | None
    metrics: dict[str, Any]
    approved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelsResponse(BaseModel):
    items: list[ModelSummary]


class OperationStatus(BaseModel):
    state: str
    mode: str
    exchange: str
    symbol: str
    timeframe: str
    selected_strategy_id: int | None
    approved_or_active_models: int
    open_positions: int
    pending_commands: int
    blockers: list[str]


class OperationalEvent(BaseModel):
    id: int
    event_type: str
    severity: str
    source: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventsResponse(BaseModel):
    items: list[OperationalEvent]


class CommandRequestCreate(BaseModel):
    command_type: CommandType
    requested_by: str = Field(default="operator", min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandRequestSummary(BaseModel):
    id: int
    command_type: str
    status: str
    requested_by: str
    payload: dict[str, Any]
    requested_at: datetime
    processed_at: datetime | None
    result: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

