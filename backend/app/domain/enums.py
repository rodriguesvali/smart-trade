from __future__ import annotations

from enum import StrEnum


class StrategyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"


class TrainingRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    TRAINED = "TRAINED"
    FAILED = "FAILED"


class TrainedModelStatus(StrEnum):
    TRAINED = "TRAINED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

