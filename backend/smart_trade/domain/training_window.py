from __future__ import annotations

from smart_trade.domain.exceptions import ValidationError


HISTORICAL_WINDOW_DAYS = 30
HOLDOUT_HOURS = 72
FEATURE_WARMUP_ROWS = 80
TIMEFRAME_MINUTES = {
    "M5": 5,
    "5M": 5,
    "5m": 5,
    "M15": 15,
    "15M": 15,
    "15m": 15,
    "M30": 30,
    "30M": 30,
    "30m": 30,
    "H1": 60,
    "1H": 60,
    "1h": 60,
    "H4": 240,
    "4H": 240,
    "4h": 240,
    "D1": 1440,
    "1D": 1440,
    "1d": 1440,
}


def calculate_training_window(timeframe: str, target_n: int) -> dict:
    timeframe_minutes = timeframe_to_minutes(timeframe)
    raw_window_rows = (HISTORICAL_WINDOW_DAYS * 24 * 60) // timeframe_minutes
    holdout_rows = (HOLDOUT_HOURS * 60) // timeframe_minutes
    usable_rows = raw_window_rows - FEATURE_WARMUP_ROWS - target_n
    train_validation_rows = usable_rows - holdout_rows
    if usable_rows <= 0 or train_validation_rows <= 0:
        raise ValidationError(
            "The selected timeframe is too coarse for a 30-day training window with 72h holdout, "
            f"{FEATURE_WARMUP_ROWS} warmup rows, and target_n={target_n}."
        )
    return {
        "mode": "timeframe_calculated",
        "historical_window_days": HISTORICAL_WINDOW_DAYS,
        "holdout_hours": HOLDOUT_HOURS,
        "timeframe": timeframe,
        "timeframe_minutes": timeframe_minutes,
        "raw_window_rows": int(raw_window_rows),
        "feature_warmup_rows": FEATURE_WARMUP_ROWS,
        "target_future_rows": int(target_n),
        "usable_rows": int(usable_rows),
        "train_validation_rows": int(train_validation_rows),
        "holdout_rows": int(holdout_rows),
        "holdout_ratio": float(holdout_rows / usable_rows),
    }


def timeframe_to_minutes(timeframe: str) -> int:
    value = timeframe.strip()
    if value in TIMEFRAME_MINUTES:
        return TIMEFRAME_MINUTES[value]
    upper = value.upper()
    if upper in TIMEFRAME_MINUTES:
        return TIMEFRAME_MINUTES[upper]
    raise ValidationError("Unsupported timeframe for calculated training window. Use M5, M15, M30, H1, H4, or D1.")
