from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    CandleFeatureRecord,
    CandleRecord,
    DataIngestionRunRecord,
    FeatureSchemaRecord,
)
from smart_trade_backend.application.market_data.features import PythonFallbackFeatureCalculator
from smart_trade_backend.application.market_data.ports import (
    FeatureCalculatorPort,
    HistoricalMarketDataPort,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.market_data import Candle, FeatureRow, FeatureSchema


@dataclass(frozen=True)
class IngestionResult:
    run: DataIngestionRunRecord
    fetched_count: int
    inserted_count: int
    feature_rows_upserted: int


def collect_historical_candles(
    session: Session,
    settings: Settings,
    market_data: HistoricalMarketDataPort,
    *,
    since_ms: int | None = None,
    limit: int | None = None,
    page_size: int = 200,
    feature_calculator: FeatureCalculatorPort | None = None,
) -> IngestionResult:
    bounded_limit = max(1, min(limit or settings.historical_ingestion_limit, 5000))
    bounded_page_size = max(1, min(page_size, settings.historical_ingestion_page_size))
    started_at = datetime.now(UTC)
    run = DataIngestionRunRecord(
        exchange=settings.exchange,
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        status="RUNNING",
        started_at=started_at,
        since_ms=since_ms,
        requested_limit=bounded_limit,
        fetched_count=0,
        inserted_count=0,
        feature_rows_upserted=0,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        candles = _fetch_pages(
            market_data,
            symbol=settings.symbol,
            timeframe=settings.timeframe,
            since_ms=since_ms,
            limit=bounded_limit,
            page_size=bounded_page_size,
        )
        inserted_count = upsert_candles(session, candles)
        apply_market_data_retention(session, settings)

        calculator = feature_calculator or PythonFallbackFeatureCalculator()
        feature_rows_upserted = generate_features_for_market(
            session,
            settings=settings,
            feature_calculator=calculator,
        )
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        run.fetched_count = len(candles)
        run.inserted_count = inserted_count
        run.feature_rows_upserted = feature_rows_upserted
        run.first_open_time_ms = candles[0].open_time_ms if candles else None
        run.last_open_time_ms = candles[-1].open_time_ms if candles else None
        run.until_ms = candles[-1].open_time_ms if candles else None
        session.commit()
        session.refresh(run)
        return IngestionResult(
            run=run,
            fetched_count=len(candles),
            inserted_count=inserted_count,
            feature_rows_upserted=feature_rows_upserted,
        )
    except Exception as exc:
        run.status = "FAILED"
        run.completed_at = datetime.now(UTC)
        run.error_message = str(exc)
        session.commit()
        raise


def _fetch_pages(
    market_data: HistoricalMarketDataPort,
    *,
    symbol: str,
    timeframe: str,
    since_ms: int | None,
    limit: int,
    page_size: int,
) -> list[Candle]:
    candles: list[Candle] = []
    cursor = since_ms
    seen_open_times: set[int] = set()

    while len(candles) < limit:
        batch = market_data.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since_ms=cursor,
            limit=min(page_size, limit - len(candles)),
        )
        if not batch:
            break

        appended = 0
        for candle in sorted(batch, key=lambda item: item.open_time_ms):
            if candle.open_time_ms in seen_open_times:
                continue
            seen_open_times.add(candle.open_time_ms)
            candles.append(candle)
            appended += 1

        if appended == 0:
            break
        cursor = candles[-1].open_time_ms + _timeframe_to_ms(timeframe)
        if len(batch) < min(page_size, limit):
            break

    return candles[:limit]


def upsert_candles(session: Session, candles: list[Candle]) -> int:
    inserted_count = 0
    for candle in candles:
        existing = session.scalar(
            select(CandleRecord).where(
                CandleRecord.exchange == candle.exchange,
                CandleRecord.symbol == candle.symbol,
                CandleRecord.timeframe == candle.timeframe,
                CandleRecord.open_time_ms == candle.open_time_ms,
            )
        )
        values = {
            "opened_at": candle.opened_at,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "source": candle.source,
            "is_closed": candle.is_closed,
            "raw_payload": candle.raw_payload or [],
        }
        if existing is None:
            session.add(
                CandleRecord(
                    exchange=candle.exchange,
                    symbol=candle.symbol,
                    timeframe=candle.timeframe,
                    open_time_ms=candle.open_time_ms,
                    **values,
                )
            )
            inserted_count += 1
        else:
            for key, value in values.items():
                setattr(existing, key, value)
    session.commit()
    return inserted_count


def generate_features_for_market(
    session: Session,
    *,
    settings: Settings,
    feature_calculator: FeatureCalculatorPort,
) -> int:
    candles = list(
        session.scalars(
            select(CandleRecord)
            .where(
                CandleRecord.exchange == settings.exchange,
                CandleRecord.symbol == settings.symbol,
                CandleRecord.timeframe == settings.timeframe,
            )
            .order_by(CandleRecord.open_time_ms)
        )
    )
    domain_candles = [
        Candle(
            exchange=record.exchange,
            symbol=record.symbol,
            timeframe=record.timeframe,
            open_time_ms=record.open_time_ms,
            opened_at=record.opened_at,
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=record.volume,
            source=record.source,
            is_closed=record.is_closed,
            raw_payload=record.raw_payload,
        )
        for record in candles
    ]
    schema = feature_calculator.feature_schema(settings.timeframe)
    ensure_feature_schema(session, schema)
    rows = feature_calculator.calculate(
        exchange=settings.exchange,
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        candles=domain_candles,
    )
    upserted = upsert_feature_rows(session, rows)
    apply_market_data_retention(session, settings)
    return upserted


def ensure_feature_schema(session: Session, schema: FeatureSchema) -> None:
    existing = session.scalar(
        select(FeatureSchemaRecord).where(FeatureSchemaRecord.schema_id == schema.schema_id)
    )
    values = {
        "name": schema.name,
        "version": schema.version,
        "timeframe": schema.timeframe,
        "features": list(schema.features),
        "parameters": schema.parameters,
    }
    if existing is None:
        session.add(FeatureSchemaRecord(schema_id=schema.schema_id, **values))
    else:
        for key, value in values.items():
            setattr(existing, key, value)
    session.commit()


def upsert_feature_rows(session: Session, rows: list[FeatureRow]) -> int:
    upserted = 0
    for row in rows:
        existing = session.scalar(
            select(CandleFeatureRecord).where(
                CandleFeatureRecord.exchange == row.exchange,
                CandleFeatureRecord.symbol == row.symbol,
                CandleFeatureRecord.timeframe == row.timeframe,
                CandleFeatureRecord.feature_schema_id == row.feature_schema_id,
                CandleFeatureRecord.open_time_ms == row.open_time_ms,
            )
        )
        values = {
            "candle_opened_at": row.candle_opened_at,
            "values": row.values,
        }
        if existing is None:
            session.add(
                CandleFeatureRecord(
                    exchange=row.exchange,
                    symbol=row.symbol,
                    timeframe=row.timeframe,
                    feature_schema_id=row.feature_schema_id,
                    open_time_ms=row.open_time_ms,
                    **values,
                )
            )
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        upserted += 1
    session.commit()
    return upserted


def market_data_status(session: Session, settings: Settings) -> dict[str, Any]:
    candle_count = session.scalar(
        select(func.count())
        .select_from(CandleRecord)
        .where(
            CandleRecord.exchange == settings.exchange,
            CandleRecord.symbol == settings.symbol,
            CandleRecord.timeframe == settings.timeframe,
        )
    ) or 0
    feature_count = session.scalar(
        select(func.count())
        .select_from(CandleFeatureRecord)
        .where(
            CandleFeatureRecord.exchange == settings.exchange,
            CandleFeatureRecord.symbol == settings.symbol,
            CandleFeatureRecord.timeframe == settings.timeframe,
        )
    ) or 0
    latest_candle = session.scalar(
        select(CandleRecord)
        .where(
            CandleRecord.exchange == settings.exchange,
            CandleRecord.symbol == settings.symbol,
            CandleRecord.timeframe == settings.timeframe,
        )
        .order_by(CandleRecord.open_time_ms.desc())
        .limit(1)
    )
    latest_feature = session.scalar(
        select(CandleFeatureRecord)
        .where(
            CandleFeatureRecord.exchange == settings.exchange,
            CandleFeatureRecord.symbol == settings.symbol,
            CandleFeatureRecord.timeframe == settings.timeframe,
        )
        .order_by(CandleFeatureRecord.open_time_ms.desc())
        .limit(1)
    )
    latest_run = session.scalar(
        select(DataIngestionRunRecord)
        .where(
            DataIngestionRunRecord.exchange == settings.exchange,
            DataIngestionRunRecord.symbol == settings.symbol,
            DataIngestionRunRecord.timeframe == settings.timeframe,
        )
        .order_by(DataIngestionRunRecord.started_at.desc())
        .limit(1)
    )
    schemas = list(
        session.scalars(select(FeatureSchemaRecord).order_by(FeatureSchemaRecord.created_at.desc()))
    )
    return {
        "exchange": settings.exchange,
        "symbol": settings.symbol,
        "timeframe": settings.timeframe,
        "candle_count": candle_count,
        "feature_count": feature_count,
        "latest_candle_opened_at": latest_candle.opened_at if latest_candle else None,
        "latest_candle_open_time_ms": latest_candle.open_time_ms if latest_candle else None,
        "latest_feature_opened_at": latest_feature.candle_opened_at if latest_feature else None,
        "latest_feature_schema_id": latest_feature.feature_schema_id if latest_feature else None,
        "feature_schemas": schemas,
        "latest_ingestion_run": latest_run,
    }


def latest_candles(session: Session, settings: Settings, *, limit: int) -> list[CandleRecord]:
    bounded_limit = max(1, min(limit, 1000))
    records = list(
        session.scalars(
            select(CandleRecord)
            .where(
                CandleRecord.exchange == settings.exchange,
                CandleRecord.symbol == settings.symbol,
                CandleRecord.timeframe == settings.timeframe,
            )
            .order_by(CandleRecord.open_time_ms.desc())
            .limit(bounded_limit)
        )
    )
    return list(reversed(records))


def apply_market_data_retention(session: Session, settings: Settings) -> None:
    now = datetime.now(UTC)
    candle_cutoff = now - timedelta(days=settings.candle_retention_days)
    feature_cutoff = now - timedelta(days=settings.feature_retention_days)
    session.execute(
        delete(CandleRecord)
        .where(CandleRecord.opened_at < candle_cutoff)
        .execution_options(synchronize_session=False)
    )
    session.execute(
        delete(CandleFeatureRecord)
        .where(CandleFeatureRecord.candle_opened_at < feature_cutoff)
        .execution_options(synchronize_session=False)
    )
    session.commit()


def _timeframe_to_ms(timeframe: str) -> int:
    match timeframe:
        case "1m":
            return 60_000
        case "3m":
            return 180_000
        case "5m":
            return 300_000
        case "15m":
            return 900_000
        case "1h":
            return 3_600_000
        case _:
            raise ValueError(f"Unsupported B3 timeframe: {timeframe}")
