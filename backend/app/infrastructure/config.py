from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    artifact_dir: Path
    global_random_seed: int
    default_symbol: str
    default_timeframe: str
    default_target_n: int
    default_take_profit_pct: float
    default_stop_loss_pct: float
    default_training_rows: int
    default_validation_ratio: float
    default_holdout_ratio: float
    default_probability_threshold: float


def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("SMART_TRADE_ENVIRONMENT", "development"),
        database_url=os.getenv(
            "SMART_TRADE_DATABASE_URL",
            "sqlite:///./var/smart_trade.db",
        ),
        artifact_dir=Path(os.getenv("SMART_TRADE_ARTIFACT_DIR", "./var/models")),
        global_random_seed=int(os.getenv("GLOBAL_RANDOM_SEED", "42")),
        default_symbol=os.getenv("SMART_TRADE_DEFAULT_SYMBOL", "BTC/USDT"),
        default_timeframe=os.getenv("SMART_TRADE_DEFAULT_TIMEFRAME", "M1"),
        default_target_n=int(os.getenv("SMART_TRADE_TARGET_N", "15")),
        default_take_profit_pct=float(os.getenv("SMART_TRADE_TARGET_TAKE_PROFIT_PCT", "0.0015")),
        default_stop_loss_pct=float(os.getenv("SMART_TRADE_TARGET_STOP_LOSS_PCT", "0.0010")),
        default_training_rows=int(os.getenv("SMART_TRADE_SYNTHETIC_TRAINING_ROWS", "900")),
        default_validation_ratio=float(os.getenv("SMART_TRADE_VALIDATION_RATIO", "0.2")),
        default_holdout_ratio=float(os.getenv("SMART_TRADE_HOLDOUT_RATIO", "0.2")),
        default_probability_threshold=float(os.getenv("SMART_TRADE_PROBABILITY_THRESHOLD", "0.55")),
    )

