import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP"] = "false"

from smart_trade_backend.adapters.persistence.models import CandleFeatureRecord, CandleRecord
from smart_trade_backend.application.market_data.features import PythonFallbackFeatureCalculator
from smart_trade_backend.application.market_data.ingestion import (
    collect_historical_candles,
    market_data_status,
)
from smart_trade_backend.config import get_settings
from smart_trade_backend.db import Base
from smart_trade_backend.domain.market_data import Candle
from smart_trade_backend.main import app


class FakeMarketDataAdapter:
    def __init__(self, candles: list[Candle]):
        self.candles = candles

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
        limit: int,
    ) -> list[Candle]:
        rows = [
            candle
            for candle in self.candles
            if candle.symbol == symbol
            and candle.timeframe == timeframe
            and (since_ms is None or candle.open_time_ms >= since_ms)
        ]
        return rows[:limit]


def prepare_schema(client: TestClient) -> None:
    Base.metadata.create_all(bind=client.app.state.db_engine)


def make_candles(count: int = 40) -> list[Candle]:
    start = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
    rows: list[Candle] = []
    for index in range(count):
        opened_at = start + timedelta(minutes=index)
        open_time_ms = int(opened_at.timestamp() * 1000)
        open_price = Decimal("67000") + Decimal(index)
        close_price = open_price + Decimal(index % 5) - Decimal("2")
        rows.append(
            Candle(
                exchange="bybit",
                symbol="BTC/USDT",
                timeframe="1m",
                open_time_ms=open_time_ms,
                opened_at=opened_at,
                open=open_price,
                high=open_price + Decimal("10"),
                low=open_price - Decimal("10"),
                close=close_price,
                volume=Decimal("1.5") + Decimal(index) / Decimal("10"),
                source="test",
                raw_payload=[open_time_ms, float(open_price), float(close_price)],
            )
        )
    return rows


def test_candle_ingestion_is_idempotent_and_generates_features() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings()
        candles = make_candles()
        adapter = FakeMarketDataAdapter(candles)

        with client.app.state.db_session_factory() as session:
            first = collect_historical_candles(
                session,
                settings,
                adapter,
                limit=40,
                page_size=15,
                feature_calculator=PythonFallbackFeatureCalculator(),
            )
            second = collect_historical_candles(
                session,
                settings,
                adapter,
                limit=40,
                page_size=15,
                feature_calculator=PythonFallbackFeatureCalculator(),
            )
            candle_count = session.query(CandleRecord).count()
            feature_count = session.query(CandleFeatureRecord).count()

    assert first.fetched_count == 40
    assert first.inserted_count == 40
    assert first.feature_rows_upserted > 0
    assert second.fetched_count == 40
    assert second.inserted_count == 0
    assert second.feature_rows_upserted == first.feature_rows_upserted
    assert candle_count == 40
    assert feature_count == first.feature_rows_upserted


def test_market_data_status_contract_reports_latest_data() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings()
        with client.app.state.db_session_factory() as session:
            collect_historical_candles(
                session,
                settings,
                FakeMarketDataAdapter(make_candles()),
                limit=40,
                page_size=20,
                feature_calculator=PythonFallbackFeatureCalculator(),
            )
            status = market_data_status(session, settings)

        response = client.get("/api/data/status")

    assert status["candle_count"] == 40
    assert status["feature_count"] > 0
    assert status["latest_ingestion_run"].status == "COMPLETED"
    assert response.status_code == 200
    assert response.json()["candle_count"] == 40
    assert response.json()["latest_ingestion_run"]["status"] == "COMPLETED"


def test_candles_endpoint_returns_chronological_rows() -> None:
    with TestClient(app) as client:
        prepare_schema(client)
        settings = get_settings()
        with client.app.state.db_session_factory() as session:
            collect_historical_candles(
                session,
                settings,
                FakeMarketDataAdapter(make_candles(5)),
                limit=5,
                feature_calculator=PythonFallbackFeatureCalculator(),
            )

        response = client.get("/api/data/candles?limit=3")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert items[0]["open_time_ms"] < items[-1]["open_time_ms"]
