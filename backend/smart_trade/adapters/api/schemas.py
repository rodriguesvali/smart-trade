from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StrategySummary(BaseModel):
    id: str
    name: str
    version: str
    description: str
    model_family: str
    status: str


class StrategyDetail(StrategySummary):
    feature_contract: dict[str, Any]
    default_parameters: dict[str, Any]
    trained_models: list["TrainedModelSummary"] = Field(default_factory=list)


class TrainingRequest(BaseModel):
    auto_validate: bool = Field(
        default=False,
        description="If true, run validation immediately after training. Swagger users can keep false and call /validate explicitly.",
    )
    exchange_id: str | None = None
    data_mode: str | None = Field(default=None, pattern="^(real|synthetic)$")
    sentiment_required: bool | None = None
    symbol: str | None = None
    sentiment_symbol: str | None = None
    timeframe: str | None = None
    target_n: int | None = Field(default=None, ge=2, le=240)
    take_profit_pct: float | None = Field(
        default=None,
        gt=0,
        lt=1,
        description="Decimal fraction target. Example: 0.01 means 1%, 0.001 means 0.1%.",
    )
    stop_loss_pct: float | None = Field(
        default=None,
        gt=0,
        lt=1,
        description="Decimal fraction target. Example: 0.01 means 1%, 0.001 means 0.1%.",
    )
    training_rows: int | None = Field(
        default=None,
        ge=180,
        le=100_000,
        description="Number of usable candles. For 90 days on M5 use 25920.",
    )


class TrainingRunRead(BaseModel):
    id: str
    strategy_id: str
    strategy_version: str
    status: str
    requested_parameters: dict[str, Any]
    window_configuration: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    model_id: str | None = None
    auto_validate: bool
    progress_phase: str | None = None
    progress_pct: float | None = None
    progress_message: str | None = None
    worker_id: str | None = None
    locked_at: datetime | None = None
    heartbeat_at: datetime | None = None


class TrainedModelSummary(BaseModel):
    id: str
    run_id: str
    strategy_id: str
    strategy_version: str
    status: str
    artifact_format: str
    created_at: datetime
    updated_at: datetime


class ValidationResultRead(BaseModel):
    id: str
    validation_type: str
    window_metadata: dict[str, Any]
    ml_metrics: dict[str, Any]
    operational_metrics: dict[str, Any]
    created_at: datetime


class TrainedModelDetail(TrainedModelSummary):
    artifact_path: str
    dataset_metadata: dict[str, Any]
    feature_schema: dict[str, Any]
    target_parameters: dict[str, Any]
    training_metrics: dict[str, Any]
    validation_summary: dict[str, Any] | None = None
    validation_results: list[ValidationResultRead] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    operator: str = "swagger-user"
    comments: str | None = None


class DeleteModelRequest(BaseModel):
    operator: str = "swagger-user"
    confirmed: bool = Field(
        default=False,
        description="Must be true to delete a REJECTED model from operational views.",
    )
    comments: str | None = None


class DeletedModelRead(BaseModel):
    model_id: str
    run_id: str
    strategy_id: str
    previous_status: str
    status: str
    artifact_cleanup: dict[str, Any]


class AuditEventRead(BaseModel):
    id: str
    event_type: str
    message: str
    payload: dict[str, Any]
    created_at: datetime
