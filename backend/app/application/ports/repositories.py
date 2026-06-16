from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities import ApprovalRecord, AuditEvent, TrainedModel, TrainingRun, TrainingStrategy, ValidationResult


class StrategyRepository(Protocol):
    def list(self) -> list[TrainingStrategy]:
        raise NotImplementedError

    def get(self, strategy_id: str) -> TrainingStrategy | None:
        raise NotImplementedError

    def save(self, strategy: TrainingStrategy) -> None:
        raise NotImplementedError


class TrainingRunRepository(Protocol):
    def get(self, run_id: str) -> TrainingRun | None:
        raise NotImplementedError

    def claim_next_pending(self, worker_id: str, timestamp: datetime) -> TrainingRun | None:
        raise NotImplementedError

    def save(self, run: TrainingRun) -> None:
        raise NotImplementedError


class TrainedModelRepository(Protocol):
    def get(self, model_id: str) -> TrainedModel | None:
        raise NotImplementedError

    def get_by_run_id(self, run_id: str) -> TrainedModel | None:
        raise NotImplementedError

    def list_by_strategy(self, strategy_id: str) -> list[TrainedModel]:
        raise NotImplementedError

    def save(self, model: TrainedModel) -> None:
        raise NotImplementedError


class ValidationResultRepository(Protocol):
    def save(self, result: ValidationResult) -> None:
        raise NotImplementedError


class ApprovalDecisionRepository(Protocol):
    def save(self, decision: ApprovalRecord) -> None:
        raise NotImplementedError


class AuditEventRepository(Protocol):
    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        raise NotImplementedError

    def save(self, event: AuditEvent) -> None:
        raise NotImplementedError
