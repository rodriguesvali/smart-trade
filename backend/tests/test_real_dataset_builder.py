from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.ml.pipeline import build_dataset_from_candles
from app.application.ports.market_data import MarketCandle
from app.application.ports.sentiment import SentimentPoint, SentimentSeries
from app.domain.exceptions import ValidationError


def test_real_dataset_builder_uses_requested_training_rows() -> None:
    candles = _candles(260)

    dataset = build_dataset_from_candles(
        candles=candles,
        exchange_id="fake",
        symbol="BTC/USDT",
        timeframe="M1",
        training_rows=180,
        target_n=8,
        take_profit_pct=0.001,
        stop_loss_pct=0.001,
        validation_ratio=0.2,
        holdout_ratio=0.2,
        sentiment_required=False,
    )

    assert dataset.features.shape == (180, 4)
    assert dataset.labels.shape == (180,)
    assert dataset.feature_metadata["dataset"]["mode"] == "real"
    assert dataset.feature_metadata["dataset"]["sentiment_status"] == "ohlcv_proxy_features"
    assert dataset.feature_metadata["feature_names"] == ["rsi_14", "open_interest_roc", "long_short_ratio", "funding_rate"]
    assert dataset.feature_metadata["dataset"]["requested_training_rows"] == 180


def test_real_dataset_builder_fails_when_sentiment_is_required() -> None:
    with pytest.raises(ValidationError, match="Real sentiment data is required"):
        build_dataset_from_candles(
            candles=_candles(220),
            exchange_id="fake",
            symbol="BTC/USDT",
            timeframe="M1",
            training_rows=180,
            target_n=8,
            take_profit_pct=0.001,
            stop_loss_pct=0.001,
            validation_ratio=0.2,
            holdout_ratio=0.2,
            sentiment_required=True,
        )


def test_real_dataset_builder_uses_real_sentiment_when_available() -> None:
    candles = _candles(260)
    sentiment = SentimentSeries(
        points=[
            SentimentPoint(
                timestamp=candle.timestamp,
                open_interest=1000 + idx,
                long_short_ratio=1.2 + (idx % 3) * 0.01,
                funding_rate=0.00001 * (idx % 5),
            )
            for idx, candle in enumerate(candles)
        ],
        metadata={"source": "test"},
    )

    dataset = build_dataset_from_candles(
        candles=candles,
        exchange_id="fake",
        symbol="BTC/USDT",
        timeframe="M1",
        training_rows=180,
        target_n=8,
        take_profit_pct=0.001,
        stop_loss_pct=0.001,
        validation_ratio=0.2,
        holdout_ratio=0.2,
        sentiment_required=True,
        sentiment=sentiment,
    )

    assert dataset.feature_metadata["dataset"]["sentiment_status"] == "ccxt_derivatives_sentiment"
    assert dataset.feature_metadata["stationarity_rules"]["funding_rate"] == "ccxt_derivatives_native_rate"


def _candles(count: int) -> list[MarketCandle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    candles: list[MarketCandle] = []
    for idx in range(count):
        price *= 1 + (0.001 if idx % 9 < 5 else -0.0007)
        candles.append(
            MarketCandle(
                timestamp=start + timedelta(minutes=idx),
                open=price * 0.999,
                high=price * 1.002,
                low=price * 0.998,
                close=price,
                volume=10 + idx % 7,
            )
        )
    return candles
