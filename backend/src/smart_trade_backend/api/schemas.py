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


class FeatureSchemaSummary(BaseModel):
    schema_id: str
    name: str
    version: str
    timeframe: str
    features: list[str]
    parameters: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataIngestionRunSummary(BaseModel):
    id: int
    exchange: str
    symbol: str
    timeframe: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    since_ms: int | None
    until_ms: int | None
    requested_limit: int | None
    fetched_count: int
    inserted_count: int
    feature_rows_upserted: int
    first_open_time_ms: int | None
    last_open_time_ms: int | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class MarketDataStatus(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    candle_count: int
    feature_count: int
    latest_candle_opened_at: datetime | None
    latest_candle_open_time_ms: int | None
    latest_feature_opened_at: datetime | None
    latest_feature_schema_id: str | None
    feature_schemas: list[FeatureSchemaSummary]
    latest_ingestion_run: DataIngestionRunSummary | None


class CandleSummary(BaseModel):
    open_time_ms: int
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_closed: bool

    model_config = ConfigDict(from_attributes=True)


class CandlesResponse(BaseModel):
    items: list[CandleSummary]


class IngestionRunCreate(BaseModel):
    since_ms: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1, le=5000)
    page_size: int = Field(default=200, ge=1, le=1000)


class FeatureGenerationResponse(BaseModel):
    feature_rows_upserted: int
