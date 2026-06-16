from __future__ import annotations

import pytest

from smart_trade.adapters.market_data.ccxt_sentiment_data_provider import (
    BINANCE_SENTIMENT_RETENTION_MS,
    _ensure_supported_sentiment_window,
    _fetch_paginated,
)
from smart_trade.domain.exceptions import ValidationError


def test_fetch_paginated_walks_forward_with_valid_windows() -> None:
    timeframe_ms = 300_000
    rows = [{"timestamp": index * timeframe_ms, "value": index} for index in range(1100)]
    windows: list[tuple[int, int]] = []

    def fetch_page(page_since: int, page_until: int) -> list[dict]:
        windows.append((page_since, page_until))
        assert page_since <= page_until
        return [row for row in rows if page_since <= row["timestamp"] <= page_until][:500]

    result = _fetch_paginated(
        fetch_page=fetch_page,
        since_ms=0,
        until_ms=rows[-1]["timestamp"],
        timeframe="5m",
        exchange=object(),
    )

    assert len(result) == 1100
    assert result[0]["timestamp"] == 0
    assert result[-1]["timestamp"] == rows[-1]["timestamp"]
    assert len(windows) == 3


def test_binance_sentiment_window_rejects_requests_beyond_public_retention() -> None:
    with pytest.raises(ValidationError, match="latest 30 days"):
        _ensure_supported_sentiment_window(
            "binance",
            since_ms=0,
            until_ms=BINANCE_SENTIMENT_RETENTION_MS + 300_000,
            timeframe="5m",
        )
