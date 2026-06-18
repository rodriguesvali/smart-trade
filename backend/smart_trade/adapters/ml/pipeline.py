from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, log_loss, precision_score
from xgboost import XGBClassifier

from smart_trade.application.ports.market_data import MarketCandle
from smart_trade.application.ports.sentiment import SentimentSeries
from smart_trade.domain.exceptions import ValidationError


FEATURE_NAMES = ["rsi_14", "open_interest_roc", "long_short_ratio", "taker_buy_sell_ratio"]


@dataclass(frozen=True)
class DatasetBundle:
    features: np.ndarray
    labels: np.ndarray
    future_returns: np.ndarray
    close_prices: np.ndarray
    high_prices: np.ndarray
    low_prices: np.ndarray
    split_indices: dict[str, tuple[int, int]]
    feature_metadata: dict


def generate_dataset(
    *,
    rows: int,
    target_n: int,
    validation_ratio: float,
    holdout_ratio: float,
    random_seed: int,
    feature_warmup_rows: int = 80,
    rsi_oversold_threshold: float = 30.0,
) -> DatasetBundle:
    rng = np.random.default_rng(random_seed)
    returns = rng.normal(0.00002, 0.0018, rows + target_n + feature_warmup_rows)
    cycle = np.sin(np.linspace(0, 20, returns.size)) * 0.0007
    price = 100_000 * np.exp(np.cumsum(returns + cycle))
    wick_pct = np.abs(rng.normal(0.00035, 0.00015, price.size))
    high = price * (1 + wick_pct)
    low = price * (1 - wick_pct)

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
    taker_buy_sell_ratio = 1.0 + 0.12 * np.sin(np.linspace(0, 25, price.size)) + rng.normal(0, 0.03, price.size)

    start = feature_warmup_rows
    usable = rows
    end = start + usable
    features = np.column_stack(
        [
            rsi[start:end],
            open_interest_roc[start:end],
            long_short_ratio[start:end],
            taker_buy_sell_ratio[start:end],
        ]
    )

    close_prices = price[start : start + usable + target_n]
    high_prices = high[start : start + usable + target_n]
    low_prices = low[start : start + usable + target_n]
    labels, future_returns = _build_labels(
        close_prices=close_prices,
        usable=usable,
        target_n=target_n,
        rsi_values=rsi[start:end],
        rsi_oversold_threshold=rsi_oversold_threshold,
    )

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
            "taker_buy_sell_ratio": "native_ratio",
            "long_short_ratio": "native_ratio",
            "rsi_14": "bounded_indicator",
        },
        "leakage_controls": {
            "global_statistics": "forbidden",
            "rolling_windows": "retrospective_only",
            "sentiment_lag": "synthetic_closed_candle_source",
        },
        "dataset": {
            "mode": "synthetic",
            "target_label_mode": "long_only_oversold_reversal_after_n_candles",
            "rsi_oversold_threshold": float(rsi_oversold_threshold),
            "feature_warmup_rows": int(feature_warmup_rows),
            "requested_training_rows": int(rows),
            "usable_rows": int(usable),
        },
    }
    return DatasetBundle(features, labels, future_returns, close_prices, high_prices, low_prices, split_indices, metadata)


def build_dataset_from_candles(
    *,
    candles: list[MarketCandle],
    exchange_id: str,
    symbol: str,
    timeframe: str,
    training_rows: int,
    target_n: int,
    validation_ratio: float,
    holdout_ratio: float,
    sentiment_required: bool,
    sentiment: SentimentSeries | None = None,
    rsi_oversold_threshold: float = 30.0,
) -> DatasetBundle:
    if sentiment_required and sentiment is None:
        raise ValidationError(
            "Real sentiment data is required, but no CCXT sentiment provider returned Open Interest, Long/Short Ratio, and Taker Buy/Sell Ratio"
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

    sentiment_status = "ccxt_derivatives_sentiment" if sentiment is not None else "ohlcv_proxy_features"
    sentiment_metadata = sentiment.metadata if sentiment is not None else {}
    if sentiment is None:
        frame["open_interest_roc"] = frame["volume"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
        returns = frame["close"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
        rolling_scale = returns.rolling(window=30, min_periods=5).std().replace(0.0, np.nan).fillna(returns.std() or 1e-9)
        frame["long_short_ratio"] = (1.0 + (returns / rolling_scale).clip(-0.25, 0.25)).fillna(1.0)
        frame["taker_buy_sell_ratio"] = 1.0
    else:
        frame = _merge_sentiment_frame(frame, sentiment)

    feature_frame = frame[FEATURE_NAMES].replace([np.inf, -np.inf], 0.0).fillna(0.0)
    start_index = len(frame) - target_n - training_rows
    if start_index < 0:
        raise ValidationError("Not enough candles to satisfy training_rows and target_n")
    usable = training_rows
    features = feature_frame.iloc[start_index : start_index + usable].to_numpy(dtype=float)
    prices = frame["close"].iloc[start_index : start_index + usable + target_n].to_numpy(dtype=float)
    highs = frame["high"].iloc[start_index : start_index + usable + target_n].to_numpy(dtype=float)
    lows = frame["low"].iloc[start_index : start_index + usable + target_n].to_numpy(dtype=float)
    labels, future_returns = _build_labels(
        close_prices=prices,
        usable=usable,
        target_n=target_n,
        rsi_values=feature_frame["rsi_14"].iloc[start_index : start_index + usable].to_numpy(dtype=float),
        rsi_oversold_threshold=rsi_oversold_threshold,
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
            "sentiment_status": sentiment_status,
            "sentiment_metadata": sentiment_metadata,
            "target_label_mode": "long_only_oversold_reversal_after_n_candles",
            "rsi_oversold_threshold": float(rsi_oversold_threshold),
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
            "open_interest_roc": "ccxt_derivatives_rate_of_change" if sentiment else "ohlcv_volume_rate_of_change_proxy",
            "taker_buy_sell_ratio": "ccxt_derivatives_native_ratio" if sentiment else "neutral_proxy_no_taker_ratio_feed",
            "long_short_ratio": "ccxt_derivatives_native_ratio" if sentiment else "ohlcv_return_pressure_proxy",
            "rsi_14": "bounded_indicator",
        },
        "leakage_controls": {
            "global_statistics": "forbidden",
            "rolling_windows": "retrospective_only",
            "closed_candles_only": True,
            "sentiment_lag": "merge_asof_backward_only" if sentiment else "not_applied_proxy_features",
        },
    }
    return DatasetBundle(features, labels, future_returns, prices, highs, lows, split_indices, metadata)


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

    model = _fit_xgboost(
        x_train=x_train,
        y_train=y_train,
        x_validation=x_validation,
        y_validation=y_validation,
        random_seed=random_seed,
        xgboost_params=xgboost_params,
        scale_pos_weight=scale_pos_weight,
    )
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


def _fit_xgboost(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    y_validation: np.ndarray,
    random_seed: int,
    xgboost_params: dict,
    scale_pos_weight: float,
) -> XGBClassifier:
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
    return model


def validate_model(
    dataset: DatasetBundle,
    artifact_path: Path,
    probability_threshold: float,
    parameters: dict | None = None,
) -> dict:
    parameters = parameters or {}
    model = XGBClassifier()
    model.load_model(artifact_path)
    holdout_start, holdout_end = dataset.split_indices["holdout"]
    x_holdout = dataset.features[holdout_start:holdout_end]
    y_holdout = dataset.labels[holdout_start:holdout_end]
    probabilities = model.predict_proba(x_holdout)[:, 1]
    ml = _ml_metrics(y_holdout, probabilities)

    target_n = int(parameters.get("target_n", 1))
    take_profit_pct = float(parameters.get("take_profit_pct", 0.0))
    stop_loss_pct = float(parameters.get("stop_loss_pct", 0.0))
    trailing_parameters = _trailing_parameters(parameters, stop_loss_pct)
    operational = _simulate_strategy_backtest(
        dataset=dataset,
        probabilities=probabilities,
        start_index=holdout_start,
        probability_threshold=probability_threshold,
        target_n=target_n,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        trailing_stop_enabled=trailing_parameters["enabled"],
        trailing_activation_pct=trailing_parameters["activation_pct"],
        trailing_distance_pct=trailing_parameters["distance_pct"],
        entry_rsi_threshold=_entry_rsi_threshold(parameters),
        fee_pct=_float_parameter(parameters, "fee_pct", 0.0),
        slippage_pct=_float_parameter(parameters, "slippage_pct", 0.0),
    )
    threshold_analysis = _threshold_analysis(
        dataset=dataset,
        probabilities=probabilities,
        start_index=holdout_start,
        configured_probability_threshold=probability_threshold,
        target_n=target_n,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        trailing_stop_enabled=trailing_parameters["enabled"],
        trailing_activation_pct=trailing_parameters["activation_pct"],
        trailing_distance_pct=trailing_parameters["distance_pct"],
        entry_rsi_threshold=_entry_rsi_threshold(parameters),
        fee_pct=_float_parameter(parameters, "fee_pct", 0.0),
        slippage_pct=_float_parameter(parameters, "slippage_pct", 0.0),
        min_trades=int(parameters.get("threshold_min_trades", 10)),
    )
    walk_forward = _walk_forward_validation(
        dataset=dataset,
        parameters=parameters,
        probability_threshold=probability_threshold,
    )
    return {
        "ml_metrics": ml,
        "operational_metrics": operational,
        "window_metadata": {
            "holdout_start_index": holdout_start,
            "holdout_end_index": holdout_end,
            "holdout_rows": int(len(x_holdout)),
            "walk_forward": walk_forward,
            "threshold_analysis": threshold_analysis,
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
        close_prices=dataset.close_prices,
        high_prices=dataset.high_prices,
        low_prices=dataset.low_prices,
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
            close_prices=_load_price_array(data, "close_prices"),
            high_prices=_load_price_array(data, "high_prices"),
            low_prices=_load_price_array(data, "low_prices"),
            split_indices=split_indices,
            feature_metadata=json.loads(data["feature_metadata"].item()),
        )


def _load_price_array(data, key: str) -> np.ndarray:
    if key in data.files:
        return data[key]
    if "close_prices" in data.files:
        return data["close_prices"]
    return _legacy_close_prices(data["future_returns"])


def _build_labels(
    *,
    close_prices: np.ndarray,
    usable: int,
    target_n: int,
    rsi_values: np.ndarray,
    rsi_oversold_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    labels = np.zeros(usable, dtype=int)
    future_returns = np.zeros(usable)
    for idx in range(usable):
        current_price = close_prices[idx]
        path = close_prices[idx + 1 : idx + target_n + 1]
        rel = (path - current_price) / current_price
        future_returns[idx] = rel[-1] if len(rel) else 0.0
        labels[idx] = int(rsi_values[idx] <= rsi_oversold_threshold and future_returns[idx] > 0)
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


def _merge_sentiment_frame(frame: pd.DataFrame, sentiment: SentimentSeries) -> pd.DataFrame:
    sentiment_frame = pd.DataFrame(
        [
            {
                "timestamp": point.timestamp,
                "open_interest": point.open_interest,
                "long_short_ratio": point.long_short_ratio,
                "taker_buy_sell_ratio": point.taker_buy_sell_ratio,
            }
            for point in sentiment.points
        ]
    ).sort_values("timestamp")
    if sentiment_frame.empty:
        raise ValidationError("Sentiment provider returned no usable rows")
    merged = pd.merge_asof(
        frame.sort_values("timestamp"),
        sentiment_frame,
        on="timestamp",
        direction="backward",
    )
    required = ["open_interest", "long_short_ratio", "taker_buy_sell_ratio"]
    if merged[required].isna().any().any():
        missing = {column: int(merged[column].isna().sum()) for column in required}
        raise ValidationError(f"Sentiment data does not cover all candle timestamps: {missing}")
    merged["open_interest_roc"] = merged["open_interest"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return merged.drop(columns=["open_interest"])


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


def _simulate_strategy_backtest(
    *,
    dataset: DatasetBundle,
    probabilities: np.ndarray,
    start_index: int,
    probability_threshold: float,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
    trailing_stop_enabled: bool,
    trailing_activation_pct: float,
    trailing_distance_pct: float,
    entry_rsi_threshold: float,
    fee_pct: float,
    slippage_pct: float,
) -> dict:
    trades: list[float] = []
    exit_reasons: dict[str, int] = {"take_profit": 0, "stop_loss": 0, "trailing_stop": 0, "time_exit": 0}
    blocked_by_position = 0
    entry_candidates = 0
    model_signals = 0
    next_available_index = start_index

    for offset, probability in enumerate(probabilities):
        row_index = start_index + offset
        is_model_signal = probability >= probability_threshold
        if is_model_signal:
            model_signals += 1
        is_entry_candidate = is_model_signal and dataset.features[row_index][0] <= entry_rsi_threshold
        if is_entry_candidate:
            entry_candidates += 1
        if row_index < next_available_index:
            if is_entry_candidate:
                blocked_by_position += 1
            continue
        if not is_entry_candidate:
            continue

        gross_return, exit_offset, exit_reason = _trade_path_return(
            close_prices=dataset.close_prices,
            high_prices=dataset.high_prices,
            low_prices=dataset.low_prices,
            row_index=row_index,
            target_n=target_n,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            trailing_stop_enabled=trailing_stop_enabled,
            trailing_activation_pct=trailing_activation_pct,
            trailing_distance_pct=trailing_distance_pct,
        )
        trades.append(gross_return - (2 * fee_pct) - (2 * slippage_pct))
        exit_reasons[exit_reason] += 1
        next_available_index = row_index + max(exit_offset, 1)

    trade_returns = np.asarray(trades, dtype=float)
    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns <= 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(abs(losses.sum())) if losses.size else 0.0
    equity = np.cumsum(trade_returns) if trade_returns.size else np.array([0.0])
    peaks = np.maximum.accumulate(equity)
    drawdowns = peaks - equity
    return {
        "signals_generated": int(model_signals),
        "entry_candidates": int(entry_candidates),
        "blocked_by_open_position": int(blocked_by_position),
        "simulated_trades": int(trade_returns.size),
        "net_result": float(trade_returns.sum()) if trade_returns.size else 0.0,
        "expectancy_per_trade": float(trade_returns.mean()) if trade_returns.size else 0.0,
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else None,
        "max_drawdown": float(drawdowns.max()) if drawdowns.size else 0.0,
        "win_rate": float((trade_returns > 0).mean()) if trade_returns.size else 0.0,
        "largest_loss_streak": _largest_loss_streak(trade_returns),
        "exit_reasons": exit_reasons,
        "probability_threshold": probability_threshold,
        "entry_rsi_threshold": entry_rsi_threshold,
        "trailing_stop_enabled": trailing_stop_enabled,
        "trailing_activation_pct": trailing_activation_pct,
        "trailing_distance_pct": trailing_distance_pct,
        "fee_pct": fee_pct,
        "slippage_pct": slippage_pct,
        "backtest_rules": [
            "closed_candle_features",
            "rsi_entry_gate",
            "model_confirmation",
            "single_open_position",
            "high_low_path_tp_sl",
            "trailing_stop_after_favorable_move",
            "conservative_same_candle_stop_first",
            "round_trip_costs",
        ],
    }


def _threshold_analysis(
    *,
    dataset: DatasetBundle,
    probabilities: np.ndarray,
    start_index: int,
    configured_probability_threshold: float,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
    trailing_stop_enabled: bool,
    trailing_activation_pct: float,
    trailing_distance_pct: float,
    entry_rsi_threshold: float,
    fee_pct: float,
    slippage_pct: float,
    min_trades: int,
) -> dict:
    rows = []
    for threshold in _threshold_grid(configured_probability_threshold):
        metrics = _simulate_strategy_backtest(
            dataset=dataset,
            probabilities=probabilities,
            start_index=start_index,
            probability_threshold=threshold,
            target_n=target_n,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            trailing_stop_enabled=trailing_stop_enabled,
            trailing_activation_pct=trailing_activation_pct,
            trailing_distance_pct=trailing_distance_pct,
            entry_rsi_threshold=entry_rsi_threshold,
            fee_pct=fee_pct,
            slippage_pct=slippage_pct,
        )
        rows.append(
            {
                "probability_threshold": threshold,
                "signals_generated": metrics["signals_generated"],
                "entry_candidates": metrics["entry_candidates"],
                "simulated_trades": metrics["simulated_trades"],
                "net_result": metrics["net_result"],
                "expectancy_per_trade": metrics["expectancy_per_trade"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "largest_loss_streak": metrics["largest_loss_streak"],
            }
        )
    recommended = _recommend_threshold(rows, min_trades)
    return {
        "thresholds": rows,
        "configured_probability_threshold": configured_probability_threshold,
        "recommended_probability_threshold": recommended["probability_threshold"] if recommended else None,
        "minimum_trades": min_trades,
        "selection_rule": "highest_profit_factor_then_net_result_with_minimum_trades_and_positive_expectancy",
    }


def _threshold_grid(configured_probability_threshold: float) -> list[float]:
    thresholds = {0.50, 0.55, 0.60, 0.65, 0.70, 0.75, round(configured_probability_threshold, 4)}
    return sorted(thresholds)


def _recommend_threshold(rows: list[dict], min_trades: int) -> dict | None:
    eligible = [
        row
        for row in rows
        if row["simulated_trades"] >= min_trades
        and row["net_result"] > 0
        and row["expectancy_per_trade"] > 0
    ]
    if not eligible:
        return None

    def sort_key(row: dict) -> tuple[float, float, int]:
        profit_factor = row["profit_factor"]
        comparable_profit_factor = float("inf") if profit_factor is None else float(profit_factor)
        return comparable_profit_factor, float(row["net_result"]), int(row["simulated_trades"])

    return max(eligible, key=sort_key)


def _trade_path_return(
    *,
    close_prices: np.ndarray,
    high_prices: np.ndarray,
    low_prices: np.ndarray,
    row_index: int,
    target_n: int,
    take_profit_pct: float,
    stop_loss_pct: float,
    trailing_stop_enabled: bool = False,
    trailing_activation_pct: float = 0.0,
    trailing_distance_pct: float = 0.0,
) -> tuple[float, int, str]:
    current_price = close_prices[row_index]
    initial_stop_price = current_price * (1 - stop_loss_pct)
    stop_price = initial_stop_price
    take_profit_price = current_price * (1 + take_profit_pct)
    activation_price = current_price * (1 + trailing_activation_pct)
    trailing_activated = False
    future_closes = close_prices[row_index + 1 : row_index + target_n + 1]
    future_highs = high_prices[row_index + 1 : row_index + target_n + 1]
    future_lows = low_prices[row_index + 1 : row_index + target_n + 1]
    if future_closes.size == 0:
        return 0.0, 1, "time_exit"

    for offset, (high, low) in enumerate(zip(future_highs, future_lows, strict=False), start=1):
        if low <= stop_price:
            exit_return = float((stop_price - current_price) / current_price)
            exit_reason = "trailing_stop" if trailing_activated and stop_price > initial_stop_price else "stop_loss"
            return exit_return, offset, exit_reason
        take_hit = high >= take_profit_price
        if take_hit:
            return take_profit_pct, offset, "take_profit"
        if trailing_stop_enabled and high >= activation_price:
            trailing_activated = True
            stop_price = max(stop_price, high * (1 - trailing_distance_pct))

    close_return = float((future_closes[-1] - current_price) / current_price)
    return close_return, int(future_closes.size), "time_exit"


def _walk_forward_validation(
    *,
    dataset: DatasetBundle,
    parameters: dict,
    probability_threshold: float,
) -> dict:
    holdout_start, _ = dataset.split_indices["holdout"]
    folds_requested = int(parameters.get("walk_forward_folds", 3))
    folds_requested = max(1, folds_requested)
    embargo_rows = max(0, int(parameters.get("walk_forward_embargo_rows", parameters.get("target_n", 1))))
    validation_size = max(1, holdout_start // (folds_requested + 1))
    completed: list[dict] = []
    skipped: list[dict] = []

    for fold_number in range(1, folds_requested + 1):
        validation_start = holdout_start - validation_size * (folds_requested - fold_number + 1)
        validation_end = validation_start + validation_size
        train_end = validation_start - embargo_rows
        if validation_start <= 0 or validation_end > holdout_start:
            skipped.append({"fold": fold_number, "reason": "insufficient_window"})
            continue
        if train_end <= 0:
            skipped.append({"fold": fold_number, "reason": "embargo_removed_training_window"})
            continue

        y_train = dataset.labels[:train_end]
        if len(set(y_train.tolist())) < 2:
            skipped.append({"fold": fold_number, "reason": "single_class_training_labels"})
            continue

        positives = int(y_train.sum())
        negatives = int(len(y_train) - positives)
        try:
            model = _fit_xgboost(
                x_train=dataset.features[:train_end],
                y_train=y_train,
                x_validation=dataset.features[validation_start:validation_end],
                y_validation=dataset.labels[validation_start:validation_end],
                random_seed=int(parameters.get("global_random_seed", 42)) + fold_number,
                xgboost_params=parameters.get("xgboost", {}),
                scale_pos_weight=negatives / max(positives, 1),
            )
        except ValueError as exc:
            skipped.append({"fold": fold_number, "reason": str(exc)})
            continue

        probabilities = model.predict_proba(dataset.features[validation_start:validation_end])[:, 1]
        ml = _ml_metrics(dataset.labels[validation_start:validation_end], probabilities)
        trailing_parameters = _trailing_parameters(parameters, float(parameters.get("stop_loss_pct", 0.0)))
        operational = _simulate_strategy_backtest(
            dataset=dataset,
            probabilities=probabilities,
            start_index=validation_start,
            probability_threshold=probability_threshold,
            target_n=int(parameters.get("target_n", 1)),
            take_profit_pct=float(parameters.get("take_profit_pct", 0.0)),
            stop_loss_pct=float(parameters.get("stop_loss_pct", 0.0)),
            trailing_stop_enabled=trailing_parameters["enabled"],
            trailing_activation_pct=trailing_parameters["activation_pct"],
            trailing_distance_pct=trailing_parameters["distance_pct"],
            entry_rsi_threshold=_entry_rsi_threshold(parameters),
            fee_pct=_float_parameter(parameters, "fee_pct", 0.0),
            slippage_pct=_float_parameter(parameters, "slippage_pct", 0.0),
        )
        completed.append(
            {
                "fold": fold_number,
                "train_start_index": 0,
                "train_end_index": train_end,
                "embargo_rows": embargo_rows,
                "validation_start_index": validation_start,
                "validation_end_index": validation_end,
                "ml_metrics": ml,
                "operational_metrics": operational,
            }
        )

    net_results = [fold["operational_metrics"]["net_result"] for fold in completed]
    trade_counts = [fold["operational_metrics"]["simulated_trades"] for fold in completed]
    precisions = [fold["ml_metrics"]["positive_precision"] for fold in completed]
    return {
        "requested_folds": folds_requested,
        "embargo_rows": embargo_rows,
        "completed_folds": len(completed),
        "skipped_folds": skipped,
        "folds": completed,
        "aggregate": {
            "total_simulated_trades": int(sum(trade_counts)),
            "mean_net_result": float(np.mean(net_results)) if net_results else 0.0,
            "profitable_folds": int(sum(result > 0 for result in net_results)),
            "mean_positive_precision": float(np.mean(precisions)) if precisions else 0.0,
        },
    }


def _entry_rsi_threshold(parameters: dict) -> float:
    for key in ("entry_rsi_threshold", "rsi_oversold_threshold", "rsi_threshold"):
        if key in parameters and parameters[key] is not None:
            return float(parameters[key])
    return 30.0


def _float_parameter(parameters: dict, key: str, default: float) -> float:
    value = parameters.get(key, default)
    if value is None:
        return default
    return float(value)


def _trailing_parameters(parameters: dict, default_stop_loss_pct: float) -> dict:
    enabled = bool(parameters.get("trailing_stop_enabled", True))
    activation = _float_parameter(parameters, "trailing_activation_pct", default_stop_loss_pct)
    distance = _float_parameter(parameters, "trailing_distance_pct", default_stop_loss_pct)
    if not enabled:
        return {"enabled": False, "activation_pct": activation, "distance_pct": distance}
    if activation <= 0:
        raise ValidationError("trailing_activation_pct must be greater than zero when trailing stop is enabled")
    if distance <= 0:
        raise ValidationError("trailing_distance_pct must be greater than zero when trailing stop is enabled")
    return {"enabled": True, "activation_pct": activation, "distance_pct": distance}


def _legacy_close_prices(future_returns: np.ndarray) -> np.ndarray:
    prices = np.ones(len(future_returns) + 1, dtype=float)
    for idx, future_return in enumerate(future_returns):
        prices[idx + 1] = prices[idx] * (1 + future_return)
    return prices
