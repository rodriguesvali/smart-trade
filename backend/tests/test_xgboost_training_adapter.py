from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from smart_trade.adapters.ml.xgboost_training_adapter import RealXGBoostTrainingAdapter
from smart_trade.application.ports.market_data import MarketCandle
from smart_trade.application.ports.sentiment import SentimentPoint, SentimentSeries
from smart_trade.domain.exceptions import ValidationError


@dataclass
class SentimentRequest:
    since: datetime
    until: datetime


class FakeMarketDataProvider:
    def __init__(self) -> None:
        self.candles = _candles(220)

    def fetch_ohlcv(self, *, exchange_id: str, symbol: str, timeframe: str, rows: int) -> list[MarketCandle]:
        return self.candles[-rows:]


class FakeSentimentDataProvider:
    def __init__(self) -> None:
        self.request: SentimentRequest | None = None

    def fetch_sentiment(
        self,
        *,
        exchange_id: str,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> SentimentSeries:
        self.request = SentimentRequest(since=since, until=until)
        points = [
            SentimentPoint(
                timestamp=candle.timestamp,
                open_interest=1000 + idx,
                long_short_ratio=1.0,
                taker_buy_sell_ratio=1.0,
            )
            for idx, candle in enumerate(_candles(220))
            if since <= candle.timestamp <= until
        ]
        return SentimentSeries(points=points, metadata={"source": "fake"})


def test_real_adapter_requests_sentiment_inside_candle_window(tmp_path) -> None:
    market_data = FakeMarketDataProvider()
    sentiment_data = FakeSentimentDataProvider()
    adapter = RealXGBoostTrainingAdapter(
        tmp_path,
        random_seed=42,
        market_data=market_data,
        sentiment_data=sentiment_data,
    )
    parameters = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "sentiment_symbol": "BTC/USDT:USDT",
        "timeframe": "M5",
        "training_rows": 180,
        "target_n": 8,
        "feature_warmup_rows": 20,
        "take_profit_pct": 0.001,
        "stop_loss_pct": 0.001,
        "validation_ratio": 0.2,
        "holdout_ratio": 0.2,
        "sentiment_required": True,
        "probability_threshold": 0.5,
        "xgboost": {"max_depth": 2, "learning_rate": 0.1, "n_estimators": 10},
    }

    try:
        adapter.train(model_id="test-model", parameters=parameters)
    except ValidationError:
        pass

    assert sentiment_data.request is not None
    fetched_candles = market_data.candles[-208:]
    assert sentiment_data.request.since == fetched_candles[0].timestamp
    assert sentiment_data.request.until == fetched_candles[-1].timestamp


def _candles(count: int) -> list[MarketCandle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    candles: list[MarketCandle] = []
    for idx in range(count):
        price *= 1 + (0.001 if idx % 9 < 5 else -0.0007)
        candles.append(
            MarketCandle(
                timestamp=start + timedelta(minutes=5 * idx),
                open=price * 0.999,
                high=price * 1.002,
                low=price * 0.998,
                close=price,
                volume=10 + idx % 7,
            )
        )
    return candles
