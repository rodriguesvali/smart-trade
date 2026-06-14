from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from smart_trade_backend.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AssetConfigurationRecord(TimestampMixin, Base):
    __tablename__ = "asset_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset: Mapped[str] = mapped_column(String(16), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(16), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    initial_capital_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_asset_configurations_active", "is_active"),
        Index("ix_asset_configurations_symbol_timeframe", "symbol", "timeframe"),
    )


class StrategyRegistryRecord(TimestampMixin, Base):
    __tablename__ = "strategy_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    supported_market: Mapped[str] = mapped_column(String(32), nullable=False)
    supported_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parameter_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    default_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    required_features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_roles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("strategy_id", "version", name="uq_strategy_registry_identity"),
        Index("ix_strategy_registry_status", "status"),
    )


class SelectedStrategyRecord(TimestampMixin, Base):
    __tablename__ = "selected_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_registry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_registry.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deselected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_selected_strategies_status", "status"),)


class ModelRegistryRecord(TimestampMixin, Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    model_role: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    feature_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_uri: Mapped[str | None] = mapped_column(String(1024))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    training_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    training_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    holdout_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    holdout_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_model_registry_status", "status"),
        Index("ix_model_registry_compatibility", "strategy_id", "strategy_version", "model_role"),
    )


class ModelTrainingRunRecord(TimestampMixin, Base):
    __tablename__ = "model_training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    model_role: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    holdout_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_model_training_runs_status", "status"),
        Index("ix_model_training_runs_model_role", "strategy_id", "strategy_version", "model_role"),
    )


class WalkForwardWindowRecord(TimestampMixin, Base):
    __tablename__ = "walk_forward_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    train_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    precision_class_1: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    predicted_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    acceptable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("model_id", "window_index", name="uq_walk_forward_model_window"),
        Index("ix_walk_forward_windows_model_id", "model_id"),
    )


class BacktestTradeRecord(TimestampMixin, Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trade_index: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    pnl: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    pnl_pct: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("model_id", "trade_index", name="uq_backtest_trades_model_index"),
        Index("ix_backtest_trades_model_id", "model_id"),
    )


class CandleRecord(TimestampMixin, Base):
    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    open_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    raw_payload: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint(
            "exchange",
            "symbol",
            "timeframe",
            "open_time_ms",
            name="uq_candles_market_time",
        ),
        Index("ix_candles_market_time", "exchange", "symbol", "timeframe", "open_time_ms"),
        Index("ix_candles_opened_at", "opened_at"),
    )


class FeatureSchemaRecord(TimestampMixin, Base):
    __tablename__ = "feature_schemas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (Index("ix_feature_schemas_identity", "name", "version"),)


class CandleFeatureRecord(TimestampMixin, Base):
    __tablename__ = "candle_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    feature_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    open_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    candle_opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "exchange",
            "symbol",
            "timeframe",
            "feature_schema_id",
            "open_time_ms",
            name="uq_candle_features_market_schema_time",
        ),
        Index(
            "ix_candle_features_market_schema_time",
            "exchange",
            "symbol",
            "timeframe",
            "feature_schema_id",
            "open_time_ms",
        ),
    )


class DataIngestionRunRecord(TimestampMixin, Base):
    __tablename__ = "data_ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    since_ms: Mapped[int | None] = mapped_column(BigInteger)
    until_ms: Mapped[int | None] = mapped_column(BigInteger)
    requested_limit: Mapped[int | None] = mapped_column(Integer)
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_rows_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_open_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_open_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_data_ingestion_runs_market_started",
            "exchange",
            "symbol",
            "timeframe",
            "started_at",
        ),
        Index("ix_data_ingestion_runs_status", "status"),
    )


class StrategyDecisionRecord(TimestampMixin, Base):
    __tablename__ = "strategy_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    participating_models: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    risk_updates: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_strategy_decisions_decided_at", "decided_at"),)


class PositionRecord(TimestampMixin, Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    average_entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    take_profit_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(255))
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_positions_status", "status"),
        Index("ix_positions_asset_status", "asset_symbol", "status"),
    )


class OrderRecord(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    exchange_order_id: Mapped[str | None] = mapped_column(String(128))
    position_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("positions.id"))
    decision_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("strategy_decisions.id"))
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    requested_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (Index("ix_orders_status", "status"),)


class FillRecord(TimestampMixin, Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    exchange_fill_id: Mapped[str | None] = mapped_column(String(128))
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    fee_asset: Mapped[str | None] = mapped_column(String(16))
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (Index("ix_fills_filled_at", "filled_at"),)


class EquitySnapshotRecord(TimestampMixin, Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    equity_usd: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    position_value_usd: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (Index("ix_equity_snapshots_snapshot_at", "snapshot_at"),)


class LiveReadinessReviewRecord(TimestampMixin, Base):
    __tablename__ = "live_readiness_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    failure_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_live_readiness_reviews_status", "status"),
        Index("ix_live_readiness_reviews_reviewed_at", "reviewed_at"),
    )


class CommandRequestRecord(TimestampMixin, Base):
    __tablename__ = "command_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_command_requests_status", "status"),
        Index("ix_command_requests_requested_at", "requested_at"),
    )


class OperationalEventRecord(Base):
    __tablename__ = "operational_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_operational_events_occurred_at", "occurred_at"),
        Index("ix_operational_events_severity", "severity"),
    )
