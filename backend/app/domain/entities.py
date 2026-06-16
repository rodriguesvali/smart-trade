from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums import ApprovalDecision, StrategyStatus, TrainedModelStatus, TrainingRunStatus
from app.domain.exceptions import InvalidStateTransitionError, ValidationError


@dataclass(frozen=True)
class TrainingStrategy:
    id: str
    name: str
    version: str
    description: str
    model_family: str
    status: StrategyStatus
    feature_contract: dict[str, Any]
    default_parameters: dict[str, Any]

    def ensure_available(self) -> None:
        if self.status != StrategyStatus.AVAILABLE:
            raise InvalidStateTransitionError("Training strategy is not available")


@dataclass
class TrainingRun:
    id: str
    strategy_id: str
    strategy_version: str
    status: TrainingRunStatus
    requested_parameters: dict[str, Any]
    window_configuration: dict[str, Any]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    model_id: str | None = None
    auto_validate: bool = False
    progress_phase: str | None = None
    progress_pct: float | None = None
    progress_message: str | None = None
    worker_id: str | None = None
    locked_at: datetime | None = None
    heartbeat_at: datetime | None = None

    def mark_running(self, timestamp: datetime, worker_id: str | None = None) -> None:
        if self.status != TrainingRunStatus.PENDING:
            raise InvalidStateTransitionError("Only PENDING training runs can start")
        self.status = TrainingRunStatus.RUNNING
        self.started_at = timestamp
        self.locked_at = timestamp
        self.heartbeat_at = timestamp
        self.worker_id = worker_id
        self.update_progress(timestamp, "training_started", 0.05, "Training run claimed by worker")

    def update_progress(self, timestamp: datetime, phase: str, pct: float, message: str | None = None) -> None:
        self.progress_phase = phase
        self.progress_pct = max(0.0, min(1.0, pct))
        self.progress_message = message
        self.heartbeat_at = timestamp

    def mark_trained(self, timestamp: datetime, model_id: str) -> None:
        if self.status != TrainingRunStatus.RUNNING:
            raise InvalidStateTransitionError("Only RUNNING training runs can finish as TRAINED")
        self.status = TrainingRunStatus.TRAINED
        self.finished_at = timestamp
        self.model_id = model_id
        self.update_progress(timestamp, "trained", 1.0, "Training completed")

    def mark_failed(self, timestamp: datetime, reason: str) -> None:
        self.status = TrainingRunStatus.FAILED
        self.finished_at = timestamp
        self.failure_reason = reason
        self.update_progress(timestamp, "failed", 1.0, reason)


@dataclass
class ValidationResult:
    id: str
    model_id: str
    validation_type: str
    window_metadata: dict[str, Any]
    ml_metrics: dict[str, Any]
    operational_metrics: dict[str, Any]
    created_at: datetime | None = None


@dataclass
class ApprovalRecord:
    id: str
    model_id: str
    decision: ApprovalDecision
    operator: str
    comments: str | None
    created_at: datetime | None = None


@dataclass
class TrainedModel:
    id: str
    run_id: str
    strategy_id: str
    strategy_version: str
    status: TrainedModelStatus
    artifact_path: str
    artifact_format: str
    feature_schema: dict[str, Any]
    target_parameters: dict[str, Any]
    training_metrics: dict[str, Any]
    validation_summary: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    validation_results: list[ValidationResult] = field(default_factory=list)
    approval_decisions: list[ApprovalRecord] = field(default_factory=list)

    def start_validation(self, timestamp: datetime) -> None:
        if self.status in {TrainedModelStatus.APPROVED, TrainedModelStatus.REJECTED}:
            raise InvalidStateTransitionError("Finalized models cannot be validated")
        self.status = TrainedModelStatus.VALIDATING
        self.updated_at = timestamp

    def complete_validation(self, timestamp: datetime, result: ValidationResult) -> None:
        if self.status != TrainedModelStatus.VALIDATING:
            raise InvalidStateTransitionError("Only VALIDATING models can complete validation")
        self.status = TrainedModelStatus.VALIDATED
        self.validation_results.append(result)
        self.validation_summary = {
            "latest_validation_result_id": result.id,
            "ml_metrics": result.ml_metrics,
            "operational_metrics": result.operational_metrics,
        }
        self.updated_at = timestamp

    def fail_validation(self, timestamp: datetime) -> None:
        self.status = TrainedModelStatus.FAILED
        self.updated_at = timestamp

    def decide(self, timestamp: datetime, decision: ApprovalDecision, record: ApprovalRecord) -> None:
        if self.status in {TrainedModelStatus.APPROVED, TrainedModelStatus.REJECTED}:
            raise InvalidStateTransitionError("Model final decision already recorded")
        if decision == ApprovalDecision.APPROVED and self.status != TrainedModelStatus.VALIDATED:
            raise InvalidStateTransitionError("Only VALIDATED models can be approved")
        if decision == ApprovalDecision.REJECTED and not record.comments:
            raise ValidationError("Rejection comments are mandatory")
        self.status = TrainedModelStatus(decision.value)
        self.approval_decisions.append(record)
        self.updated_at = timestamp


@dataclass(frozen=True)
class AuditEvent:
    id: str
    event_type: str
    message: str
    payload: dict[str, Any]
    created_at: datetime | None = None
