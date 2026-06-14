from fastapi import APIRouter, Query

from smart_trade_backend.api.dependencies import SessionDep
from smart_trade_backend.api.schemas import (
    CommandRequestCreate,
    CommandRequestSummary,
    ConfigurationSummary,
    EventsResponse,
    ModelsResponse,
    OperationStatus,
    StrategiesResponse,
)
from smart_trade_backend.application.commands import create_command_request
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


@router.post("/commands", response_model=CommandRequestSummary, status_code=201)
def post_command(request: CommandRequestCreate, session: SessionDep):
    return create_command_request(
        session,
        command_type=request.command_type,
        requested_by=request.requested_by,
        payload=request.payload,
    )
