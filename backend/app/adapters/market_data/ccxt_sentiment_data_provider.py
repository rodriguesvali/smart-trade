from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from time import sleep

import ccxt

from app.adapters.market_data.ccxt_market_data_provider import TIMEFRAME_MS, to_ccxt_timeframe
from app.application.ports.sentiment import SentimentPoint, SentimentSeries
from app.domain.exceptions import ValidationError


class CcxtSentimentDataProvider:
    def fetch_sentiment(
        self,
        *,
        exchange_id: str,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> SentimentSeries:
        exchange = self._build_exchange(exchange_id)
        market_symbol = _derivative_symbol(symbol)
        ccxt_timeframe = _sentiment_timeframe(timeframe)
        since_ms = _to_ms(since)
        until_ms = _to_ms(until)
        limit = _limit_for_range(since_ms, until_ms, ccxt_timeframe)

        if not exchange.has.get("fetchOpenInterestHistory"):
            raise ValidationError(f"Exchange {exchange_id} does not support open interest history through CCXT")
        if not exchange.has.get("fetchLongShortRatioHistory"):
            raise ValidationError(f"Exchange {exchange_id} does not support long/short ratio history through CCXT")
        if not exchange.has.get("fetchFundingRateHistory"):
            raise ValidationError(f"Exchange {exchange_id} does not support funding rate history through CCXT")

        open_interest = exchange.fetch_open_interest_history(
            market_symbol,
            ccxt_timeframe,
            since_ms,
            limit,
            {"until": until_ms},
        )
        self._sleep(exchange)
        long_short = exchange.fetch_long_short_ratio_history(
            market_symbol,
            ccxt_timeframe,
            since_ms,
            limit,
            {"until": until_ms},
        )
        self._sleep(exchange)
        funding = exchange.fetch_funding_rate_history(
            market_symbol,
            since_ms,
            max(1, ceil((until_ms - since_ms) / (8 * 60 * 60 * 1000)) + 3),
            {"until": until_ms},
        )

        points = _merge_sentiment(open_interest, long_short, funding)
        if not points:
            raise ValidationError(f"CCXT returned no sentiment rows for {exchange_id} {market_symbol}")
        return SentimentSeries(
            points=points,
            metadata={
                "source": "ccxt.derivatives",
                "symbol": market_symbol,
                "timeframe": ccxt_timeframe,
                "open_interest_rows": len(open_interest),
                "long_short_ratio_rows": len(long_short),
                "funding_rate_rows": len(funding),
                "start_timestamp": points[0].timestamp.isoformat(),
                "end_timestamp": points[-1].timestamp.isoformat(),
            },
        )

    def _build_exchange(self, exchange_id: str):
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValidationError(f"Unsupported CCXT exchange_id: {exchange_id}")
        return exchange_class({"enableRateLimit": True})

    def _sleep(self, exchange) -> None:
        if getattr(exchange, "rateLimit", 0):
            sleep(float(exchange.rateLimit) / 1000.0)


def _merge_sentiment(open_interest: list[dict], long_short: list[dict], funding: list[dict]) -> list[SentimentPoint]:
    oi_values = {
        int(item["timestamp"]): float(item.get("openInterestAmount") or item.get("openInterestValue") or 0.0)
        for item in open_interest
        if item.get("timestamp") is not None
    }
    long_short_values = {
        int(item["timestamp"]): float(item["longShortRatio"])
        for item in long_short
        if item.get("timestamp") is not None and item.get("longShortRatio") is not None
    }
    funding_values = {
        int(item["timestamp"]): float(item["fundingRate"])
        for item in funding
        if item.get("timestamp") is not None and item.get("fundingRate") is not None
    }
    timestamps = sorted(set(oi_values) | set(long_short_values) | set(funding_values))
    if not timestamps:
        return []
    points: list[SentimentPoint] = []
    latest_oi: float | None = None
    latest_long_short: float | None = None
    latest_funding: float | None = None
    for timestamp_ms in timestamps:
        latest_oi = oi_values.get(timestamp_ms, latest_oi)
        latest_long_short = long_short_values.get(timestamp_ms, latest_long_short)
        latest_funding = funding_values.get(timestamp_ms, latest_funding)
        if latest_oi is None or latest_long_short is None or latest_funding is None:
            continue
        points.append(
            SentimentPoint(
                timestamp=datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc),
                open_interest=latest_oi,
                long_short_ratio=latest_long_short,
                funding_rate=latest_funding,
            )
        )
    return points


def _sentiment_timeframe(timeframe: str) -> str:
    ccxt_timeframe = to_ccxt_timeframe(timeframe)
    if TIMEFRAME_MS[ccxt_timeframe] < TIMEFRAME_MS["5m"]:
        return "5m"
    return ccxt_timeframe


def _limit_for_range(since_ms: int, until_ms: int, timeframe: str) -> int:
    return min(500, max(10, ceil((until_ms - since_ms) / TIMEFRAME_MS[timeframe]) + 5))


def _to_ms(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _derivative_symbol(symbol: str) -> str:
    if ":" in symbol:
        return symbol
    if "/" not in symbol:
        raise ValidationError(f"Cannot derive contract symbol from {symbol}")
    base, quote = symbol.split("/", 1)
    return f"{base}/{quote}:{quote}"
