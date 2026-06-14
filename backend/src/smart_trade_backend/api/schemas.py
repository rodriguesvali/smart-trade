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
    parameter_schema: dict[str, Any]
    required_features: list[str]
    model_roles: list[dict[str, Any]]
    default_parameters: dict[str, Any]
    compatibility: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class StrategiesResponse(BaseModel):
    selected_strategy_id: int | None
    items: list[StrategySummary]


class SelectedStrategyCreate(BaseModel):
    strategy_registry_id: int = Field(ge=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class SelectedStrategySummary(BaseModel):
    id: int
    strategy_registry_id: int
    status: str
    parameters: dict[str, Any]
    selected_at: datetime
    deselected_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


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
    parameters: dict[str, Any]
    training_window_start: datetime | None
    training_window_end: datetime | None
    holdout_start: datetime | None
    holdout_end: datetime | None
    approved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelsResponse(BaseModel):
    items: list[ModelSummary]


class ModelTrainingRunSummary(BaseModel):
    id: int
    model_id: str
    model_role: str
    strategy_id: str
    strategy_version: str
    feature_schema_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    training_rows: int
    holdout_rows: int
    metrics: dict[str, Any]
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class ModelTrainingRunsResponse(BaseModel):
    items: list[ModelTrainingRunSummary]


class ModelTrainingResponse(BaseModel):
    items: list[ModelSummary]


class ModelApprovalResponse(BaseModel):
    model: ModelSummary


class WalkForwardWindowSummary(BaseModel):
    id: int
    model_id: str
    window_index: int
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    precision_class_1: Decimal
    predicted_positive_count: int
    actual_positive_count: int
    acceptable: bool
    metrics: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class BacktestTradeSummary(BaseModel):
    id: int
    model_id: str
    trade_index: int
    entry_at: datetime
    exit_at: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    pnl_pct: Decimal
    exit_reason: str

    model_config = ConfigDict(from_attributes=True)


class ModelEvidenceResponse(BaseModel):
    windows: list[WalkForwardWindowSummary]
    trades: list[BacktestTradeSummary]


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


class PaperRunCreate(BaseModel):
    limit: int = Field(default=500, ge=1, le=5000)


class PaperRunResponse(BaseModel):
    processed_candles: int
    decisions_created: int
    orders_created: int
    fills_created: int
    equity_snapshots_created: int
    open_position_id: int | None


class PaperPositionSummary(BaseModel):
    id: int
    asset_symbol: str
    status: str
    side: str
    quantity: Decimal
    average_entry_price: Decimal
    stop_loss_price: Decimal | None
    take_profit_price: Decimal | None
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None
    strategy_id: str
    strategy_version: str
    model_refs: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class PaperEquitySummary(BaseModel):
    id: int
    asset_symbol: str
    equity_usd: Decimal
    cash_usd: Decimal
    position_value_usd: Decimal
    snapshot_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)


class PaperDecisionSummary(BaseModel):
    id: int
    strategy_id: str
    strategy_version: str
    asset_symbol: str
    timeframe: str
    action: str
    reason: str
    confidence: Decimal | None
    participating_models: list[dict[str, Any]]
    risk_updates: dict[str, Any]
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperOrderSummary(BaseModel):
    id: int
    client_order_id: str
    exchange_order_id: str | None
    position_id: int | None
    decision_id: int | None
    asset_symbol: str
    side: str
    order_type: str
    status: str
    requested_quantity: Decimal
    requested_price: Decimal | None
    submitted_at: datetime | None
    raw_request: dict[str, Any]
    raw_response: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class PaperStatusResponse(BaseModel):
    open_position: PaperPositionSummary | None
    latest_equity: PaperEquitySummary | None
    recent_decisions: list[PaperDecisionSummary]
    recent_orders: list[PaperOrderSummary]


class LiveReadinessReviewSummary(BaseModel):
    id: int
    status: str
    requested_by: str
    reviewed_at: datetime
    enabled_at: datetime | None
    checks: list[dict[str, Any]]
    evidence: dict[str, Any]
    failure_reasons: list[str]

    model_config = ConfigDict(from_attributes=True)


class LiveReadinessStatusResponse(BaseModel):
    ready: bool
    checks: list[dict[str, Any]]
    failure_reasons: list[str]
    latest_review: LiveReadinessReviewSummary | None


class LiveReadinessEnableCreate(BaseModel):
    requested_by: str = Field(default="operator", min_length=1, max_length=128)


class LiveReadinessEnableResponse(BaseModel):
    review: LiveReadinessReviewSummary


class LiveOrderCreate(BaseModel):
    side: str = Field(pattern="^(BUY|SELL)$")
    idempotency_key: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_-]+$")
    requested_by: str = Field(default="operator", min_length=1, max_length=128)
    quote_amount_usd: Decimal | None = Field(default=None, gt=0)


class LiveOrderResponse(BaseModel):
    order: PaperOrderSummary
    duplicate: bool


class LiveStatusResponse(BaseModel):
    live_enabled_by_config: bool
    manual_readiness_enabled: bool
    pending_order_count: int
    open_position: PaperPositionSummary | None
    recent_orders: list[PaperOrderSummary]
    latest_readiness_review: LiveReadinessReviewSummary | None


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
