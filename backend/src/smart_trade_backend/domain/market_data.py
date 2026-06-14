from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Candle:
    exchange: str
    symbol: str
    timeframe: str
    open_time_ms: int
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source: str = "ccxt"
    is_closed: bool = True
    raw_payload: list[object] | None = None


@dataclass(frozen=True)
class FeatureSchema:
    schema_id: str
    name: str
    version: str
    timeframe: str
    features: tuple[str, ...]
    parameters: dict[str, object]


@dataclass(frozen=True)
class FeatureRow:
    exchange: str
    symbol: str
    timeframe: str
    feature_schema_id: str
    open_time_ms: int
    candle_opened_at: datetime
    values: dict[str, float]


def utc_datetime_from_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def decimal_from_number(value: object) -> Decimal:
    return Decimal(str(value))
