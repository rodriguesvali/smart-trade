from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TrainingOutput:
    artifact_path: str
    artifact_format: str
    feature_schema: dict
    target_parameters: dict
    training_metrics: dict


@dataclass(frozen=True)
class ValidationOutput:
    validation_type: str
    window_metadata: dict
    ml_metrics: dict
    operational_metrics: dict


@dataclass(frozen=True)
class ArtifactDeletionResult:
    artifact_path: str
    artifact_deleted: bool
    dataset_path: str | None = None
    dataset_deleted: bool = False


class ModelTrainer(Protocol):
    def train(self, *, model_id: str, parameters: dict) -> TrainingOutput:
        raise NotImplementedError


class ModelValidator(Protocol):
    def validate(self, *, artifact_path: str, parameters: dict) -> ValidationOutput:
        raise NotImplementedError


class ModelArtifactStore(Protocol):
    def delete(self, artifact_path: str) -> ArtifactDeletionResult:
        raise NotImplementedError
