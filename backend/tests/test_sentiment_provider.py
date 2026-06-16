from __future__ import annotations

from app.adapters.market_data.ccxt_sentiment_data_provider import _fetch_paginated


def test_fetch_paginated_walks_back_from_until() -> None:
    timeframe_ms = 300_000
    rows = [{"timestamp": index * timeframe_ms, "value": index} for index in range(1100)]

    def fetch_page(until_cursor: int) -> list[dict]:
        available = [row for row in rows if row["timestamp"] <= until_cursor]
        return available[-500:]

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
