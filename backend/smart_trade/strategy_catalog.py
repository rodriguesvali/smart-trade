from __future__ import annotations

from smart_trade.application.ports.repositories import StrategyRepository
from smart_trade.domain.entities import TrainingStrategy
from smart_trade.domain.enums import StrategyStatus
from smart_trade.domain.training_window import calculate_training_window
from smart_trade.infrastructure.config import get_settings


STRATEGY_ID = "rsi_sentiment_xgboost_m1"


def strategy_payload() -> dict:
    settings = get_settings()
    default_window = calculate_training_window(settings.default_timeframe, settings.default_target_n)
    return {
        "id": STRATEGY_ID,
        "name": "RSI Sentiment XGBoost",
        "version": "1.0.0",
        "description": (
            "Binary XGBoost training strategy combining RSI/IFR with Open Interest, "
            "Long/Short Ratio, and Taker Buy/Sell Ratio sentiment features."
        ),
        "model_family": "XGBoost",
        "status": "AVAILABLE",
        "feature_contract": {
            "technical": ["rsi_14"],
            "sentiment": ["open_interest_roc", "long_short_ratio", "taker_buy_sell_ratio"],
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
            "rsi_oversold_threshold": 30.0,
            "training_rows": default_window["usable_rows"],
            "validation_ratio": settings.default_validation_ratio,
            "holdout_ratio": default_window["holdout_ratio"],
            "feature_warmup_rows": default_window["feature_warmup_rows"],
            "training_window_policy": default_window,
            "xgboost": {
                "max_depth": 3,
                "learning_rate": 0.08,
                "n_estimators": 60,
                "subsample": 0.9,
                "colsample_bytree": 0.9,
            },
            "validation": {
                "probability_threshold": settings.default_probability_threshold,
                "take_profit_pct": settings.default_take_profit_pct,
                "stop_loss_pct": settings.default_stop_loss_pct,
                "trailing_stop_enabled": True,
                "trailing_activation_pct": settings.default_stop_loss_pct,
                "trailing_distance_pct": settings.default_stop_loss_pct,
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
