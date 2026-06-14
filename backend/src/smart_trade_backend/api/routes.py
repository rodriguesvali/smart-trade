from fastapi import APIRouter, HTTPException, Query

from smart_trade_backend.adapters.exchange.ccxt_public import (
    CcxtPublicMarketDataAdapter,
    CcxtUnavailableError,
)
from smart_trade_backend.adapters.features.talib import (
    TalibFeatureCalculator,
    TalibUnavailableError,
)
from smart_trade_backend.api.dependencies import SessionDep
from smart_trade_backend.api.schemas import (
    CandlesResponse,
    CommandRequestCreate,
    CommandRequestSummary,
    ConfigurationSummary,
    DataIngestionRunSummary,
    EventsResponse,
    FeatureGenerationResponse,
    IngestionRunCreate,
    MarketDataStatus,
    ModelsResponse,
    OperationStatus,
    StrategiesResponse,
)
from smart_trade_backend.application.commands import create_command_request
from smart_trade_backend.application.market_data.features import PythonFallbackFeatureCalculator
from smart_trade_backend.application.market_data.ingestion import (
    collect_historical_candles,
    generate_features_for_market,
    latest_candles,
    market_data_status,
)
from smart_trade_backend.application.read_models import (
    configuration_summary,
    get_selected_strategy,
    latest_events,
    list_models,
    list_strategies,
    operation_status,
)
from smart_trade_backend.config import get_settings

router = APIRouter(prefix="/api", tags=["operator-read-models"])


@router.get("/health")
def get_api_health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/configuration/summary", response_model=ConfigurationSummary)
def get_configuration_summary() -> dict:
    return configuration_summary(get_settings())


@router.get("/strategies", response_model=StrategiesResponse)
def get_strategies(session: SessionDep) -> dict:
    selected_strategy = get_selected_strategy(session)
    return {
        "selected_strategy_id": selected_strategy.strategy_registry_id
        if selected_strategy is not None
        else None,
        "items": list_strategies(session),
    }


@router.get("/models", response_model=ModelsResponse)
def get_models(session: SessionDep) -> dict:
    return {"items": list_models(session)}


@router.get("/operation/status", response_model=OperationStatus)
def get_operation_status(session: SessionDep) -> dict:
    return operation_status(session, get_settings())


@router.get("/events", response_model=EventsResponse)
def get_events(session: SessionDep, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {"items": latest_events(session, limit)}


@router.get("/data/status", response_model=MarketDataStatus)
def get_market_data_status(session: SessionDep) -> dict:
    return market_data_status(session, get_settings())


@router.get("/data/candles", response_model=CandlesResponse)
def get_candles(session: SessionDep, limit: int = Query(default=200, ge=1, le=1000)) -> dict:
    return {"items": latest_candles(session, get_settings(), limit=limit)}


@router.post("/data/ingestion-runs", response_model=DataIngestionRunSummary, status_code=201)
def post_data_ingestion_run(request: IngestionRunCreate, session: SessionDep):
    settings = get_settings()
    try:
        result = collect_historical_candles(
            session,
            settings,
            CcxtPublicMarketDataAdapter(exchange_id=settings.exchange),
            since_ms=request.since_ms,
            limit=request.limit,
            page_size=request.page_size,
            feature_calculator=_feature_calculator(),
        )
    except CcxtUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TalibUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result.run


@router.post("/data/features/generate", response_model=FeatureGenerationResponse)
def post_feature_generation(session: SessionDep) -> dict:
    try:
        feature_rows_upserted = generate_features_for_market(
            session,
            settings=get_settings(),
            feature_calculator=_feature_calculator(),
        )
    except TalibUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"feature_rows_upserted": feature_rows_upserted}


@router.post("/commands", response_model=CommandRequestSummary, status_code=201)
def post_command(request: CommandRequestCreate, session: SessionDep):
    return create_command_request(
        session,
        command_type=request.command_type,
        requested_by=request.requested_by,
        payload=request.payload,
    )


def _feature_calculator():
    try:
        import numpy  # noqa: F401
        import talib  # noqa: F401
    except ImportError:
        return PythonFallbackFeatureCalculator()
    return TalibFeatureCalculator()
