from __future__ import annotations

from app.application.ports.repositories import StrategyRepository
from app.domain.entities import TrainingStrategy
from app.domain.enums import StrategyStatus
from app.infrastructure.config import get_settings


STRATEGY_ID = "rsi_sentiment_xgboost_m1"


def strategy_payload() -> dict:
    settings = get_settings()
    return {
        "id": STRATEGY_ID,
        "name": "RSI Sentiment XGBoost M1",
        "version": "1.0.0",
        "description": (
            "Binary XGBoost training strategy combining RSI/IFR with Open Interest, "
            "Long/Short Ratio, and Funding Rate sentiment features."
        ),
        "model_family": "XGBoost",
        "status": "AVAILABLE",
        "feature_contract": {
            "technical": ["rsi_14"],
            "sentiment": ["open_interest_roc", "long_short_ratio", "funding_rate"],
            "leakage_controls": [
                "chronological_split",
                "rolling_or_train_fitted_statistics_only",
                "sentiment_lag_when_required",
            ],
        },
        "default_parameters": {
            "exchange_id": settings.default_exchange_id,
            "data_mode": settings.data_mode,
            "sentiment_required": settings.sentiment_required,
            "symbol": settings.default_symbol,
            "timeframe": settings.default_timeframe,
            "target_n": settings.default_target_n,
            "take_profit_pct": settings.default_take_profit_pct,
            "stop_loss_pct": settings.default_stop_loss_pct,
            "training_rows": settings.default_training_rows,
            "validation_ratio": settings.default_validation_ratio,
            "holdout_ratio": settings.default_holdout_ratio,
            "probability_threshold": settings.default_probability_threshold,
            "xgboost": {
                "max_depth": 3,
                "learning_rate": 0.08,
                "n_estimators": 60,
                "subsample": 0.9,
                "colsample_bytree": 0.9,
            },
        },
    }


def strategy_entity() -> TrainingStrategy:
    payload = strategy_payload()
    return TrainingStrategy(
        id=payload["id"],
        name=payload["name"],
        version=payload["version"],
        description=payload["description"],
        model_family=payload["model_family"],
        status=StrategyStatus(payload["status"]),
        feature_contract=payload["feature_contract"],
        default_parameters=payload["default_parameters"],
    )


def seed_strategy_catalog(repository: StrategyRepository) -> None:
    repository.save(strategy_entity())
