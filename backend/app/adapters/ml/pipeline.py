from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, log_loss, precision_score
from xgboost import XGBClassifier


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

