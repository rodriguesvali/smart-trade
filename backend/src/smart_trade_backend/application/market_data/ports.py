from typing import Protocol

from smart_trade_backend.domain.market_data import Candle, FeatureRow, FeatureSchema


class HistoricalMarketDataPort(Protocol):
    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
        limit: int,
    ) -> list[Candle]:
        """Fetch OHLCV candles in chronological order."""


class FeatureCalculatorPort(Protocol):
    def feature_schema(self, timeframe: str) -> FeatureSchema:
        """Return the schema produced by this calculator."""

    def calculate(
        self,
        *,
        exchange: str,
        symbol: str,
        timeframe: str,
        candles: list[Candle],
    ) -> list[FeatureRow]:
        """Calculate feature rows using only present and prior candle data."""
