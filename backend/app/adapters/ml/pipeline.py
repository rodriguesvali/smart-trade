from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, log_loss, precision_score
from xgboost import XGBClassifier

from app.application.ports.market_data import MarketCandle
from app.domain.exceptions import ValidationError


FEATURE_NAMES = ["rsi_14", "open_interest_roc", "long_short_ratio", "cvd_delta"]


@dataclass(frozen=True)
class DatasetBundle:
    features: np.ndarray
    labels: np.ndarray
    future_returns: np.ndarray
    split_indices: dict[str, tuple[int, int]]
    feature_metadata: dict


def generate_dataset(
    *,
    rows: int,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
    validation_ratio: float,
    holdout_ratio: float,
    random_seed: int,
) -> DatasetBundle:
    rng = np.random.default_rng(random_seed)
    returns = rng.normal(0.00002, 0.0018, rows + target_n + 80)
    cycle = np.sin(np.linspace(0, 20, returns.size)) * 0.0007
    price = 100_000 * np.exp(np.cumsum(returns + cycle))

    deltas = np.diff(price, prepend=price[0])
    gains = np.clip(deltas, 0, None)
    losses = np.clip(-deltas, 0, None)
    avg_gain = _rolling_mean(gains, 14)
    avg_loss = _rolling_mean(losses, 14)
    rs = avg_gain / np.maximum(avg_loss, 1e-9)
    rsi = 100 - (100 / (1 + rs))

    open_interest = 1_000_000 + np.cumsum(rng.normal(0, 750, price.size))
    open_interest_roc = np.diff(open_interest, prepend=open_interest[0]) / np.maximum(
        np.abs(np.roll(open_interest, 1)),
        1,
    )
    open_interest_roc[0] = 0

    long_short_ratio = 1.0 + 0.18 * np.sin(np.linspace(0, 15, price.size)) + rng.normal(0, 0.035, price.size)
    cvd = np.cumsum(np.sign(deltas) * rng.uniform(50, 400, price.size))
    cvd_delta = np.diff(cvd, prepend=cvd[0])

    start = 40
    usable = rows
    end = start + usable
    features = np.column_stack(
        [
            rsi[start:end],
            open_interest_roc[start:end],
            long_short_ratio[start:end],
            cvd_delta[start:end] / 1000.0,
        ]
    )

    labels = np.zeros(usable, dtype=int)
    future_returns = np.zeros(usable)
    for idx in range(usable):
        current_price = price[start + idx]
        path = price[start + idx + 1 : start + idx + target_n + 1]
        rel = (path - current_price) / current_price
        future_returns[idx] = rel[-1] if len(rel) else 0.0
        take_hits = np.where(rel >= take_profit_pct)[0]
        stop_hits = np.where(rel <= -stop_loss_pct)[0]
        first_take = int(take_hits[0]) if take_hits.size else None
        first_stop = int(stop_hits[0]) if stop_hits.size else None
        labels[idx] = int(first_take is not None and (first_stop is None or first_take < first_stop))

    train_end = int(usable * (1 - validation_ratio - holdout_ratio))
    validation_end = int(usable * (1 - holdout_ratio))
    split_indices = {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "holdout": (validation_end, usable),
    }
    metadata = {
        "feature_names": FEATURE_NAMES,
        "stationarity_rules": {
            "open_interest_roc": "rate_of_change_retrospective",
            "cvd_delta": "per_candle_delta_scaled",
            "long_short_ratio": "native_ratio",
            "rsi_14": "bounded_indicator",
        },
        "leakage_controls": {
            "global_statistics": "forbidden",
            "rolling_windows": "retrospective_only",
            "sentiment_lag": "synthetic_closed_candle_source",
        },
    }
    return DatasetBundle(features, labels, future_returns, split_indices, metadata)


def build_dataset_from_candles(
    *,
    candles: list[MarketCandle],
    exchange_id: str,
    symbol: str,
    timeframe: str,
    training_rows: int,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
    validation_ratio: float,
    holdout_ratio: float,
    sentiment_required: bool,
) -> DatasetBundle:
    if sentiment_required:
        raise ValidationError(
            "Real sentiment data is required, but no CCXT sentiment provider is available for this strategy yet"
        )
    minimum_rows = training_rows + target_n
    if len(candles) < minimum_rows:
        raise ValidationError(f"At least {minimum_rows} candles are required to build the training dataset")

    frame = pd.DataFrame(
        [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]
    ).sort_values("timestamp")
    _ensure_no_duplicate_timestamps(frame)

    deltas = frame["close"].diff().fillna(0.0)
    gains = deltas.clip(lower=0.0)
    losses = (-deltas).clip(lower=0.0)
    avg_gain = gains.rolling(window=14, min_periods=14).mean()
    avg_loss = losses.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    frame["rsi_14"] = (100 - (100 / (1 + rs))).fillna(50.0)

    # These are OHLCV-derived placeholders, not true sentiment feeds. They keep
    # the real-candle flow trainable while the CCXT sentiment provider is added.
    frame["open_interest_roc"] = frame["volume"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    returns = frame["close"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    rolling_scale = returns.rolling(window=30, min_periods=5).std().replace(0.0, np.nan).fillna(returns.std() or 1e-9)
    frame["long_short_ratio"] = (1.0 + (returns / rolling_scale).clip(-0.25, 0.25)).fillna(1.0)
    cvd_proxy = (np.sign(deltas) * frame["volume"]).cumsum()
    frame["cvd_delta"] = cvd_proxy.diff().fillna(0.0)

    feature_frame = frame[FEATURE_NAMES].replace([np.inf, -np.inf], 0.0).fillna(0.0)
    start_index = len(frame) - target_n - training_rows
    if start_index < 0:
        raise ValidationError("Not enough candles to satisfy training_rows and target_n")
    usable = training_rows
    features = feature_frame.iloc[start_index : start_index + usable].to_numpy(dtype=float)
    prices = frame["close"].iloc[start_index : start_index + usable + target_n].to_numpy(dtype=float)
    labels, future_returns = _build_labels(
        prices=prices,
        usable=usable,
        target_n=target_n,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
    )
    split_indices = _split_indices(usable, validation_ratio, holdout_ratio)
    if split_indices["train"][1] <= split_indices["train"][0]:
        raise ValidationError("Training split is empty; increase training_rows or reduce validation/holdout ratios")

    metadata = {
        "feature_names": FEATURE_NAMES,
        "dataset": {
            "mode": "real",
            "exchange_id": exchange_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "ccxt.fetch_ohlcv",
            "sentiment_required": sentiment_required,
            "sentiment_status": "ohlcv_proxy_features",
            "raw_candle_count": len(candles),
            "requested_training_rows": int(training_rows),
            "usable_rows": int(usable),
            "start_timestamp": frame["timestamp"].iloc[0].isoformat(),
            "end_timestamp": frame["timestamp"].iloc[-1].isoformat(),
            "usable_start_timestamp": frame["timestamp"].iloc[start_index].isoformat(),
            "usable_end_timestamp": frame["timestamp"].iloc[start_index + usable - 1].isoformat(),
            "split_indices": split_indices,
        },
        "stationarity_rules": {
            "open_interest_roc": "ohlcv_volume_rate_of_change_proxy",
            "cvd_delta": "ohlcv_directional_volume_delta_proxy",
            "long_short_ratio": "ohlcv_return_pressure_proxy",
            "rsi_14": "bounded_indicator",
        },
        "leakage_controls": {
            "global_statistics": "forbidden",
            "rolling_windows": "retrospective_only",
            "closed_candles_only": True,
            "sentiment_lag": "not_applied_proxy_features",
        },
    }
    return DatasetBundle(features, labels, future_returns, split_indices, metadata)


def train_xgboost(
    dataset: DatasetBundle,
    artifact_path: Path,
    random_seed: int,
    xgboost_params: dict,
) -> tuple[dict, XGBClassifier]:
    train_start, train_end = dataset.split_indices["train"]
    validation_start, validation_end = dataset.split_indices["validation"]

    x_train = dataset.features[train_start:train_end]
    y_train = dataset.labels[train_start:train_end]
    x_validation = dataset.features[validation_start:validation_end]
    y_validation = dataset.labels[validation_start:validation_end]

    positives = int(y_train.sum())
    negatives = int(len(y_train) - positives)
    if len(set(y_train.tolist())) < 2:
        raise ValidationError("Training labels contain a single class; adjust target or data window parameters")
    scale_pos_weight = negatives / max(positives, 1)

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=random_seed,
        seed=random_seed,
        max_depth=int(xgboost_params.get("max_depth", 3)),
        learning_rate=float(xgboost_params.get("learning_rate", 0.08)),
        n_estimators=int(xgboost_params.get("n_estimators", 60)),
        subsample=float(xgboost_params.get("subsample", 0.9)),
        colsample_bytree=float(xgboost_params.get("colsample_bytree", 0.9)),
        scale_pos_weight=float(xgboost_params.get("scale_pos_weight", scale_pos_weight)),
    )
    model.fit(x_train, y_train, eval_set=[(x_validation, y_validation)], verbose=False)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(artifact_path)

    probabilities = model.predict_proba(x_validation)[:, 1]
    metrics = _ml_metrics(y_validation, probabilities)
    metrics.update(
        {
            "training_rows": int(len(x_train)),
            "validation_rows": int(len(x_validation)),
            "positive_training_rows": positives,
            "negative_training_rows": negatives,
        }
    )
    return metrics, model


def validate_model(
    dataset: DatasetBundle,
    artifact_path: Path,
    probability_threshold: float,
) -> dict:
    model = XGBClassifier()
    model.load_model(artifact_path)
    holdout_start, holdout_end = dataset.split_indices["holdout"]
    x_holdout = dataset.features[holdout_start:holdout_end]
    y_holdout = dataset.labels[holdout_start:holdout_end]
    holdout_returns = dataset.future_returns[holdout_start:holdout_end]
    probabilities = model.predict_proba(x_holdout)[:, 1]
    ml = _ml_metrics(y_holdout, probabilities)

    signals = probabilities >= probability_threshold
    trade_returns = holdout_returns[signals]
    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns <= 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(abs(losses.sum())) if losses.size else 0.0
    equity = np.cumsum(trade_returns) if trade_returns.size else np.array([0.0])
    peaks = np.maximum.accumulate(equity)
    drawdowns = peaks - equity
    operational = {
        "signals_generated": int(signals.sum()),
        "simulated_trades": int(trade_returns.size),
        "net_result": float(trade_returns.sum()) if trade_returns.size else 0.0,
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else None,
        "max_drawdown": float(drawdowns.max()) if drawdowns.size else 0.0,
        "win_rate": float((trade_returns > 0).mean()) if trade_returns.size else 0.0,
        "largest_loss_streak": _largest_loss_streak(trade_returns),
        "probability_threshold": probability_threshold,
    }
    return {
        "ml_metrics": ml,
        "operational_metrics": operational,
        "window_metadata": {
            "holdout_start_index": holdout_start,
            "holdout_end_index": holdout_end,
            "holdout_rows": int(len(x_holdout)),
        },
    }


def _rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        result[idx] = values[start : idx + 1].mean()
    return result


def save_dataset(dataset: DatasetBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        features=dataset.features,
        labels=dataset.labels,
        future_returns=dataset.future_returns,
        split_indices=json.dumps(dataset.split_indices),
        feature_metadata=json.dumps(dataset.feature_metadata),
    )


def load_dataset(path: Path) -> DatasetBundle:
    if not path.exists():
        raise ValidationError(f"Training dataset artifact not found: {path}")
    with np.load(path, allow_pickle=False) as data:
        split_indices = {
            key: tuple(value)
            for key, value in json.loads(data["split_indices"].item()).items()
        }
        return DatasetBundle(
            features=data["features"],
            labels=data["labels"],
            future_returns=data["future_returns"],
            split_indices=split_indices,
            feature_metadata=json.loads(data["feature_metadata"].item()),
        )


def _build_labels(
    *,
    prices: np.ndarray,
    usable: int,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> tuple[np.ndarray, np.ndarray]:
    labels = np.zeros(usable, dtype=int)
    future_returns = np.zeros(usable)
    for idx in range(usable):
        current_price = prices[idx]
        path = prices[idx + 1 : idx + target_n + 1]
        rel = (path - current_price) / current_price
        future_returns[idx] = rel[-1] if len(rel) else 0.0
        take_hits = np.where(rel >= take_profit_pct)[0]
        stop_hits = np.where(rel <= -stop_loss_pct)[0]
        first_take = int(take_hits[0]) if take_hits.size else None
        first_stop = int(stop_hits[0]) if stop_hits.size else None
        labels[idx] = int(first_take is not None and (first_stop is None or first_take < first_stop))
    return labels, future_returns


def _split_indices(usable: int, validation_ratio: float, holdout_ratio: float) -> dict[str, tuple[int, int]]:
    train_end = int(usable * (1 - validation_ratio - holdout_ratio))
    validation_end = int(usable * (1 - holdout_ratio))
    return {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "holdout": (validation_end, usable),
    }


def _ensure_no_duplicate_timestamps(frame: pd.DataFrame) -> None:
    if frame["timestamp"].duplicated().any():
        raise ValidationError("Market data contains duplicate candle timestamps")


def _ml_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    predictions = probabilities >= 0.5
    labels_for_logloss = labels
    if len(set(labels.tolist())) < 2:
        labels_for_logloss = np.append(labels, 1 - labels[0])
        probabilities_for_logloss = np.append(probabilities, 1 - probabilities[0])
    else:
        probabilities_for_logloss = probabilities
    return {
        "positive_precision": float(precision_score(labels, predictions, zero_division=0)),
        "f1_score": float(f1_score(labels, predictions, zero_division=0)),
        "log_loss": float(log_loss(labels_for_logloss, probabilities_for_logloss, labels=[0, 1])),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "positive_class_count": int(labels.sum()),
        "row_count": int(len(labels)),
    }


def _largest_loss_streak(trade_returns: np.ndarray) -> int:
    largest = 0
    current = 0
    for value in trade_returns:
        if value <= 0:
            current += 1
            largest = max(largest, current)
        else:
            current = 0
    return largest
