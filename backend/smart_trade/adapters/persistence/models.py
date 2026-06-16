from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_trade.infrastructure.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrainingStrategyRecord(Base):
    __tablename__ = "training_strategies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    model_family: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_contract: Mapped[dict] = mapped_column(JSON, nullable=False)
    default_parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    runs: Mapped[list["TrainingRunRecord"]] = relationship(back_populates="strategy")
    models: Mapped[list["TrainedModelRecord"]] = relationship(back_populates="strategy")


class TrainingRunRecord(Base):
    __tablename__ = "training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("training_strategies.id"), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    window_configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    auto_validate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    progress_phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
    progress_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    strategy: Mapped[TrainingStrategyRecord] = relationship(back_populates="runs")
    model: Mapped["TrainedModelRecord | None"] = relationship(back_populates="run")


class TrainedModelRecord(Base):
    __tablename__ = "trained_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("training_runs.id"), nullable=False, unique=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("training_strategies.id"), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_format: Mapped[str] = mapped_column(String(20), nullable=False)
    feature_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    target_parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    training_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[TrainingRunRecord] = relationship(back_populates="model")
    strategy: Mapped[TrainingStrategyRecord] = relationship(back_populates="models")
    validation_results: Mapped[list["TrainingValidationResultRecord"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )
    approval_decisions: Mapped[list["TrainingApprovalDecisionRecord"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )


class TrainingValidationResultRecord(Base):
    __tablename__ = "training_validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("trained_models.id"), nullable=False)
    validation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    window_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    ml_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    operational_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    model: Mapped[TrainedModelRecord] = relationship(back_populates="validation_results")


class TrainingApprovalDecisionRecord(Base):
    __tablename__ = "training_approval_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("trained_models.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    operator: Mapped[str] = mapped_column(String(120), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    model: Mapped[TrainedModelRecord] = relationship(back_populates="approval_decisions")


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
