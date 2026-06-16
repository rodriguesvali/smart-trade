from __future__ import annotations

from datetime import datetime, timezone
from time import sleep

import ccxt

from smart_trade.application.ports.market_data import MarketCandle
from smart_trade.domain.exceptions import ValidationError


TIMEFRAME_ALIASES = {
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

TIMEFRAME_MS = {
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


class CcxtMarketDataProvider:
    def fetch_ohlcv(self, *, exchange_id: str, symbol: str, timeframe: str, rows: int) -> list[MarketCandle]:
        if rows <= 0:
            raise ValidationError("Requested market data rows must be positive")
        exchange = self._build_exchange(exchange_id)
        ccxt_timeframe = to_ccxt_timeframe(timeframe)
        if not exchange.has.get("fetchOHLCV"):
            raise ValidationError(f"Exchange {exchange_id} does not support public OHLCV through CCXT")

        timeframe_ms = TIMEFRAME_MS[ccxt_timeframe]
        # Leave the current candle out; only closed candles can enter the training dataset.
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - timeframe_ms
        since_ms = end_ms - ((rows + 5) * timeframe_ms)
        collected: dict[int, list] = {}

        while len(collected) < rows:
            batch = exchange.fetch_ohlcv(symbol, ccxt_timeframe, since=since_ms, limit=min(1000, rows - len(collected) + 5))
            if not batch:
                break
            for candle in batch:
                timestamp_ms = int(candle[0])
                if timestamp_ms <= end_ms:
                    collected[timestamp_ms] = candle
            last_timestamp = int(batch[-1][0])
            next_since = last_timestamp + timeframe_ms
            if next_since <= since_ms:
                break
            since_ms = next_since
            if getattr(exchange, "rateLimit", 0):
                sleep(float(exchange.rateLimit) / 1000.0)

        candles = [
            MarketCandle(
                timestamp=datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc),
                open=float(raw[1]),
                high=float(raw[2]),
                low=float(raw[3]),
                close=float(raw[4]),
                volume=float(raw[5]),
            )
            for timestamp_ms, raw in sorted(collected.items())
        ]
        candles = candles[-rows:]
        if len(candles) < rows:
            raise ValidationError(
                f"CCXT returned {len(candles)} closed candles for {exchange_id} {symbol} {timeframe}; {rows} required"
            )
        return candles

    def _build_exchange(self, exchange_id: str):
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValidationError(f"Unsupported CCXT exchange_id: {exchange_id}")
        return exchange_class({"enableRateLimit": True})


def to_ccxt_timeframe(timeframe: str) -> str:
    value = timeframe.strip()
    upper = value.upper()
    normalized = TIMEFRAME_ALIASES.get(upper, value)
    if normalized not in TIMEFRAME_MS:
        raise ValidationError(
            f"Unsupported timeframe for CCXT training data: {timeframe}. Use M5, M15, M30, H1, H4, or D1."
        )
    return normalized
