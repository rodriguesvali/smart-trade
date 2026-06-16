from __future__ import annotations

from datetime import datetime, timezone
from time import sleep

import ccxt

from app.adapters.market_data.ccxt_market_data_provider import TIMEFRAME_MS, to_ccxt_timeframe
from app.application.ports.sentiment import SentimentPoint, SentimentSeries
from app.domain.exceptions import ValidationError


MAX_PAGE_LIMIT = 500
BINANCE_SENTIMENT_RETENTION_MS = 30 * 24 * 60 * 60 * 1000


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
        _ensure_supported_sentiment_window(exchange_id, since_ms, until_ms, ccxt_timeframe)

        if not exchange.has.get("fetchOpenInterestHistory"):
            raise ValidationError(f"Exchange {exchange_id} does not support open interest history through CCXT")
        if not exchange.has.get("fetchLongShortRatioHistory"):
            raise ValidationError(f"Exchange {exchange_id} does not support long/short ratio history through CCXT")
        open_interest = _fetch_open_interest_history(
            exchange=exchange,
            symbol=market_symbol,
            timeframe=ccxt_timeframe,
            since_ms=since_ms,
            until_ms=until_ms,
        )
        self._sleep(exchange)
        long_short = _fetch_long_short_ratio_history(
            exchange=exchange,
            symbol=market_symbol,
            timeframe=ccxt_timeframe,
            since_ms=since_ms,
            until_ms=until_ms,
        )
        self._sleep(exchange)
        taker_ratio = _fetch_taker_buy_sell_ratio(
            exchange=exchange,
            exchange_id=exchange_id,
            symbol=market_symbol,
            timeframe=ccxt_timeframe,
            since_ms=since_ms,
            until_ms=until_ms,
        )

        points = _merge_sentiment(open_interest, long_short, taker_ratio)
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
                "taker_buy_sell_ratio_rows": len(taker_ratio),
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


def _fetch_taker_buy_sell_ratio(
    *,
    exchange,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int,
) -> list[dict]:
    if exchange_id != "binance":
        raise ValidationError(
            f"Exchange {exchange_id} taker buy/sell ratio is not implemented yet; Binance USDT futures is supported"
        )
    raw_symbol = _contract_symbol_id(symbol)
    return _fetch_paginated(
        fetch_page=lambda page_since, page_until: exchange.fapidata_get_takerlongshortratio(
            {
                "symbol": raw_symbol,
                "period": timeframe,
                "startTime": page_since,
                "endTime": page_until,
                "limit": MAX_PAGE_LIMIT,
            }
        ),
        since_ms=since_ms,
        until_ms=until_ms,
        timeframe=timeframe,
        exchange=exchange,
    )


def _fetch_open_interest_history(
    *,
    exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int,
) -> list[dict]:
    return _fetch_paginated(
        fetch_page=lambda page_since, page_until: exchange.fetch_open_interest_history(
            symbol,
            timeframe,
            page_since,
            MAX_PAGE_LIMIT,
            {"until": page_until},
        ),
        since_ms=since_ms,
        until_ms=until_ms,
        timeframe=timeframe,
        exchange=exchange,
    )


def _fetch_long_short_ratio_history(
    *,
    exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int,
) -> list[dict]:
    return _fetch_paginated(
        fetch_page=lambda page_since, page_until: exchange.fetch_long_short_ratio_history(
            symbol,
            timeframe,
            page_since,
            MAX_PAGE_LIMIT,
            {"until": page_until},
        ),
        since_ms=since_ms,
        until_ms=until_ms,
        timeframe=timeframe,
        exchange=exchange,
    )


def _fetch_paginated(*, fetch_page, since_ms: int, until_ms: int, timeframe: str, exchange) -> list[dict]:
    timeframe_ms = TIMEFRAME_MS[timeframe]
    page_span_ms = (MAX_PAGE_LIMIT - 1) * timeframe_ms
    cursor = since_ms
    rows_by_timestamp: dict[int, dict] = {}
    while cursor <= until_ms:
        page_until = min(cursor + page_span_ms, until_ms)
        batch = fetch_page(cursor, page_until)
        if not batch:
            cursor = page_until + timeframe_ms
            continue
        timestamps = [int(item["timestamp"]) for item in batch if item.get("timestamp") is not None]
        for item in batch:
            timestamp = item.get("timestamp")
            if timestamp is None:
                continue
            timestamp_ms = int(timestamp)
            if since_ms <= timestamp_ms <= until_ms:
                rows_by_timestamp[timestamp_ms] = item
        if not timestamps:
            cursor = page_until + timeframe_ms
            continue
        next_cursor = max(timestamps) + timeframe_ms
        if next_cursor <= cursor:
            break
        cursor = max(next_cursor, page_until + timeframe_ms)
        if getattr(exchange, "rateLimit", 0):
            sleep(float(exchange.rateLimit) / 1000.0)
    return [rows_by_timestamp[timestamp] for timestamp in sorted(rows_by_timestamp)]


def _ensure_supported_sentiment_window(exchange_id: str, since_ms: int, until_ms: int, timeframe: str) -> None:
    if until_ms < since_ms:
        raise ValidationError("Sentiment window is invalid: until must be greater than or equal to since")
    if exchange_id != "binance":
        return
    if until_ms - since_ms <= BINANCE_SENTIMENT_RETENTION_MS:
        return
    timeframe_minutes = TIMEFRAME_MS[timeframe] // 60_000
    max_rows = BINANCE_SENTIMENT_RETENTION_MS // TIMEFRAME_MS[timeframe]
    raise ValidationError(
        "Binance public derivatives sentiment endpoints only expose roughly the latest 30 days "
        f"for Open Interest, Long/Short Ratio, and Taker Buy/Sell Ratio. "
        f"The requested sentiment window is {(until_ms - since_ms) / 86_400_000:.1f} days on {timeframe}. "
        f"Use a shorter window, about {max_rows} candles on {timeframe_minutes}m, "
        "or configure a historical sentiment provider for multi-month training."
    )


def _merge_sentiment(open_interest: list[dict], long_short: list[dict], taker_ratio: list[dict]) -> list[SentimentPoint]:
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
    taker_values = {
        int(item["timestamp"]): float(item["buySellRatio"])
        for item in taker_ratio
        if item.get("timestamp") is not None and item.get("buySellRatio") is not None
    }
    timestamps = sorted(set(oi_values) | set(long_short_values) | set(taker_values))
    if not timestamps:
        return []
    points: list[SentimentPoint] = []
    latest_oi: float | None = None
    latest_long_short: float | None = None
    latest_taker_ratio: float | None = None
    for timestamp_ms in timestamps:
        latest_oi = oi_values.get(timestamp_ms, latest_oi)
        latest_long_short = long_short_values.get(timestamp_ms, latest_long_short)
        latest_taker_ratio = taker_values.get(timestamp_ms, latest_taker_ratio)
        if latest_oi is None or latest_long_short is None or latest_taker_ratio is None:
            continue
        points.append(
            SentimentPoint(
                timestamp=datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc),
                open_interest=latest_oi,
                long_short_ratio=latest_long_short,
                taker_buy_sell_ratio=latest_taker_ratio,
            )
        )
    return points


def _sentiment_timeframe(timeframe: str) -> str:
    return to_ccxt_timeframe(timeframe)


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


def _contract_symbol_id(symbol: str) -> str:
    base_quote = symbol.split(":", 1)[0]
    if "/" not in base_quote:
        return base_quote
    base, quote = base_quote.split("/", 1)
    return f"{base}{quote}"
