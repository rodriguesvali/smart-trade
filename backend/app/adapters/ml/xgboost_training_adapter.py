from __future__ import annotations

from pathlib import Path

from app.application.ports.market_data import MarketDataProvider
from app.application.ports.ml import TrainingOutput, ValidationOutput
from app.adapters.ml.pipeline import (
    build_dataset_from_candles,
    generate_dataset,
    load_dataset,
    save_dataset,
    train_xgboost,
    validate_model,
)


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
        dataset_path = self.artifact_dir / f"{model_id}.dataset.npz"
        save_dataset(dataset, dataset_path)
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
        dataset = load_dataset(Path(artifact_path).with_suffix(".dataset.npz"))
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


class RealXGBoostTrainingAdapter:
    def __init__(self, artifact_dir: Path, random_seed: int, market_data: MarketDataProvider) -> None:
        self.artifact_dir = artifact_dir
        self.random_seed = random_seed
        self.market_data = market_data

    def train(self, *, model_id: str, parameters: dict) -> TrainingOutput:
        rows = int(parameters["training_rows"])
        target_n = int(parameters["target_n"])
        candle_rows = rows + target_n + 80
        exchange_id = str(parameters["exchange_id"])
        symbol = str(parameters["symbol"])
        timeframe = str(parameters["timeframe"])
        candles = self.market_data.fetch_ohlcv(
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            rows=candle_rows,
        )
        dataset = build_dataset_from_candles(
            candles=candles,
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            training_rows=rows,
            target_n=target_n,
            take_profit_pct=float(parameters["take_profit_pct"]),
            stop_loss_pct=float(parameters["stop_loss_pct"]),
            validation_ratio=float(parameters["validation_ratio"]),
            holdout_ratio=float(parameters["holdout_ratio"]),
            sentiment_required=bool(parameters.get("sentiment_required", False)),
        )
        artifact_path = self.artifact_dir / f"{model_id}.json"
        dataset_path = self.artifact_dir / f"{model_id}.dataset.npz"
        save_dataset(dataset, dataset_path)
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
        dataset = load_dataset(Path(artifact_path).with_suffix(".dataset.npz"))
        result = validate_model(
            dataset=dataset,
            artifact_path=Path(artifact_path),
            probability_threshold=float(parameters["probability_threshold"]),
        )
        return ValidationOutput(
            validation_type="walk_forward_and_holdout",
            window_metadata=result["window_metadata"] | dataset.feature_metadata.get("dataset", {}),
            ml_metrics=result["ml_metrics"],
            operational_metrics=result["operational_metrics"],
        )
