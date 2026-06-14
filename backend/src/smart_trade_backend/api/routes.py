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
    LiveOrderCreate,
    LiveOrderResponse,
    LiveReadinessEnableCreate,
    LiveReadinessEnableResponse,
    LiveReadinessStatusResponse,
    LiveStatusResponse,
    MarketDataStatus,
    ModelApprovalResponse,
    ModelEvidenceResponse,
    ModelsResponse,
    ModelTrainingResponse,
    ModelTrainingRunsResponse,
    OperationStatus,
    PaperRunCreate,
    PaperRunResponse,
    PaperStatusResponse,
    SelectedStrategyCreate,
    SelectedStrategySummary,
    StrategiesResponse,
    StrategySummary,
)
from smart_trade_backend.application.commands import create_command_request
from smart_trade_backend.application.live.execution import (
    LiveExecutionError,
    execute_live_order,
    latest_live_status,
)
from smart_trade_backend.application.market_data.features import PythonFallbackFeatureCalculator
from smart_trade_backend.application.market_data.ingestion import (
    collect_historical_candles,
    generate_features_for_market,
    latest_candles,
    market_data_status,
)
from smart_trade_backend.application.model_training.service import (
    ModelApprovalError,
    ModelTrainingError,
    approve_model,
    backtest_trades_for_model,
    latest_training_runs,
    train_selected_strategy_models,
    walk_forward_windows_for_model,
)
from smart_trade_backend.application.paper.runtime import (
    PaperRuntimeError,
    latest_paper_status,
    run_paper_replay,
)
from smart_trade_backend.application.read_models import (
    configuration_summary,
    get_selected_strategy,
    latest_events,
    list_models,
    list_strategies,
    operation_status,
)
from smart_trade_backend.application.readiness.live import (
    LiveReadinessError,
    enable_live_readiness,
    live_readiness_status,
)
from smart_trade_backend.application.strategy.registry import (
    StrategySelectionError,
    register_available_strategies,
    select_strategy,
    strategy_compatibility,
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
    settings = get_settings()
    register_available_strategies(session)
    selected_strategy = get_selected_strategy(session)
    return {
        "selected_strategy_id": selected_strategy.strategy_registry_id
        if selected_strategy is not None
        else None,
        "items": [
            _strategy_summary(record, strategy_compatibility(session, settings, record))
            for record in list_strategies(session)
        ],
    }


@router.post("/strategies/register", response_model=StrategiesResponse)
def post_strategy_registration(session: SessionDep) -> dict:
    settings = get_settings()
    register_available_strategies(session)
    selected_strategy = get_selected_strategy(session)
    return {
        "selected_strategy_id": selected_strategy.strategy_registry_id
        if selected_strategy is not None
        else None,
        "items": [
            _strategy_summary(record, strategy_compatibility(session, settings, record))
            for record in list_strategies(session)
        ],
    }


@router.post("/strategies/select", response_model=SelectedStrategySummary, status_code=201)
def post_strategy_selection(request: SelectedStrategyCreate, session: SessionDep):
    try:
        return select_strategy(
            session,
            get_settings(),
            strategy_registry_id=request.strategy_registry_id,
            parameters=request.parameters,
        )
    except StrategySelectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models", response_model=ModelsResponse)
def get_models(session: SessionDep) -> dict:
    return {"items": list_models(session)}


@router.post("/models/train", response_model=ModelTrainingResponse, status_code=201)
def post_model_training(session: SessionDep) -> dict:
    try:
        return {"items": train_selected_strategy_models(session, get_settings())}
    except ModelTrainingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/models/{model_id}/approve", response_model=ModelApprovalResponse)
def post_model_approval(model_id: str, session: SessionDep) -> dict:
    try:
        return {"model": approve_model(session, get_settings(), model_id=model_id)}
    except ModelApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/training-runs", response_model=ModelTrainingRunsResponse)
def get_model_training_runs(
    session: SessionDep, limit: int = Query(default=20, ge=1, le=100)
) -> dict:
    return {"items": latest_training_runs(session, limit=limit)}


@router.get("/models/{model_id}/evidence", response_model=ModelEvidenceResponse)
def get_model_evidence(model_id: str, session: SessionDep) -> dict:
    return {
        "windows": walk_forward_windows_for_model(session, model_id),
        "trades": backtest_trades_for_model(session, model_id),
    }


@router.get("/operation/status", response_model=OperationStatus)
def get_operation_status(session: SessionDep) -> dict:
    return operation_status(session, get_settings())


@router.get("/paper/status", response_model=PaperStatusResponse)
def get_paper_status(session: SessionDep) -> dict:
    return latest_paper_status(session, get_settings())


@router.post("/paper/runs", response_model=PaperRunResponse, status_code=201)
def post_paper_run(request: PaperRunCreate, session: SessionDep):
    try:
        return run_paper_replay(session, get_settings(), limit=request.limit)
    except PaperRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/live-readiness/status", response_model=LiveReadinessStatusResponse)
def get_live_readiness_status(session: SessionDep) -> dict:
    return live_readiness_status(session, get_settings())


@router.post(
    "/live-readiness/enable",
    response_model=LiveReadinessEnableResponse,
    status_code=201,
)
def post_live_readiness_enable(request: LiveReadinessEnableCreate, session: SessionDep) -> dict:
    try:
        return {
            "review": enable_live_readiness(
                session,
                get_settings(),
                requested_by=request.requested_by,
            )
        }
    except LiveReadinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/live/status", response_model=LiveStatusResponse)
def get_live_status(session: SessionDep) -> dict:
    return latest_live_status(session, get_settings())


@router.post("/live/orders", response_model=LiveOrderResponse, status_code=201)
def post_live_order(request: LiveOrderCreate, session: SessionDep) -> dict:
    try:
        result = execute_live_order(
            session,
            get_settings(),
            side=request.side,  # type: ignore[arg-type]
            idempotency_key=request.idempotency_key,
            requested_by=request.requested_by,
            quote_amount_usd=request.quote_amount_usd,
        )
    except LiveExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"order": result.order, "duplicate": result.duplicate}


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
        settings=get_settings(),
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


def _strategy_summary(record, compatibility: dict) -> StrategySummary:
    return StrategySummary.model_validate(record).model_copy(
        update={"compatibility": compatibility}
    )
