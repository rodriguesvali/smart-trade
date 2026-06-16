from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MarketCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    def fetch_ohlcv(self, *, exchange_id: str, symbol: str, timeframe: str, rows: int) -> list[MarketCandle]:
        raise NotImplementedError
