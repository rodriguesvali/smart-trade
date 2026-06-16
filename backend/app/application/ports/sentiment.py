from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SentimentPoint:
    timestamp: datetime
    open_interest: float
    long_short_ratio: float
    funding_rate: float


@dataclass(frozen=True)
class SentimentSeries:
    points: list[SentimentPoint]
    metadata: dict


class SentimentDataProvider(Protocol):
    def fetch_sentiment(
        self,
        *,
        exchange_id: str,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> SentimentSeries:
        raise NotImplementedError
