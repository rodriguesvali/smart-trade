from __future__ import annotations

from pathlib import Path

from app.application.ports.ml import TrainingOutput, ValidationOutput
from app.adapters.ml.pipeline import generate_dataset, train_xgboost, validate_model


class SyntheticXGBoostTrainingAdapter:
    """Development adapter for deterministic MVP training.

    This adapter owns XGBoost, NumPy and artifact filesystem details. The
    application layer only depends on the ModelTrainer/ModelValidator ports.
    """

    def __init__(self, artifact_dir: Path, random_seed: int) -> None:
        self.artifact_dir = artifact_dir
        self.random_seed = random_seed

    def train(self, *, model_id: str, parameters: dict) -> TrainingOutput:
        dataset = generate_dataset(
            rows=int(parameters["training_rows"]),
            target_n=int(parameters["target_n"]),
            take_profit_pct=float(parameters["take_profit_pct"]),
            stop_loss_pct=float(parameters["stop_loss_pct"]),
            validation_ratio=float(parameters["validation_ratio"]),
            holdout_ratio=float(parameters["holdout_ratio"]),
            random_seed=int(parameters.get("global_random_seed", self.random_seed)),
        )
        artifact_path = self.artifact_dir / f"{model_id}.json"
        training_metrics, _ = train_xgboost(
            dataset=dataset,
            artifact_path=artifact_path,
            random_seed=int(parameters.get("global_random_seed", self.random_seed)),
            xgboost_params=parameters["xgboost"],
        )
        return TrainingOutput(
            artifact_path=str(artifact_path),
            artifact_format="json",
            feature_schema=dataset.feature_metadata,
            target_parameters={
                "target_n": parameters["target_n"],
                "take_profit_pct": parameters["take_profit_pct"],
                "stop_loss_pct": parameters["stop_loss_pct"],
            },
            training_metrics=training_metrics,
        )

    def validate(self, *, artifact_path: str, parameters: dict) -> ValidationOutput:
        dataset = generate_dataset(
            rows=int(parameters["training_rows"]),
            target_n=int(parameters["target_n"]),
            take_profit_pct=float(parameters["take_profit_pct"]),
            stop_loss_pct=float(parameters["stop_loss_pct"]),
            validation_ratio=float(parameters["validation_ratio"]),
            holdout_ratio=float(parameters["holdout_ratio"]),
            random_seed=int(parameters.get("global_random_seed", self.random_seed)),
        )
        result = validate_model(
            dataset=dataset,
            artifact_path=Path(artifact_path),
            probability_threshold=float(parameters["probability_threshold"]),
        )
        return ValidationOutput(
            validation_type="walk_forward_and_holdout",
            window_metadata=result["window_metadata"],
            ml_metrics=result["ml_metrics"],
            operational_metrics=result["operational_metrics"],
        )
