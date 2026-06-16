from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_trade.application.use_cases.training import (
    DecisionCommand,
    DeleteModelCommand,
    DeletedModelResult,
    TrainingCommand,
    TrainingUseCases,
)
from smart_trade.domain.entities import AuditEvent, TrainedModel, TrainingRun, TrainingStrategy, ValidationResult
from smart_trade.domain.exceptions import DomainError, InvalidStateTransitionError, NotFoundError, ValidationError
from smart_trade.infrastructure.container import build_training_use_cases
from smart_trade.infrastructure.database import get_session
from smart_trade.adapters.api.schemas import (
    ApprovalRequest,
    AuditEventRead,
    DeletedModelRead,
    DeleteModelRequest,
    StrategyDetail,
    StrategySummary,
    TrainedModelDetail,
    TrainedModelSummary,
    TrainingRequest,
    TrainingRunRead,
    ValidationResultRead,
)

router = APIRouter(prefix="/api")


def get_use_cases(session: Session = Depends(get_session)) -> TrainingUseCases:
    return build_training_use_cases(session)


@router.get("/strategies", response_model=list[StrategySummary], tags=["strategies"])
def list_strategies(use_cases: TrainingUseCases = Depends(get_use_cases)) -> list[StrategySummary]:
    return [_strategy_summary(strategy) for strategy in use_cases.list_strategies()]


@router.get("/strategies/{strategy_id}", response_model=StrategyDetail, tags=["strategies"])
def get_strategy(strategy_id: str, use_cases: TrainingUseCases = Depends(get_use_cases)) -> StrategyDetail:
    try:
        strategy = use_cases.get_strategy(strategy_id)
        models = use_cases.list_models_for_strategy(strategy_id)
        return StrategyDetail(
            **_strategy_summary(strategy).model_dump(),
            feature_contract=strategy.feature_contract,
            default_parameters=strategy.default_parameters,
            trained_models=[_model_summary(model) for model in models],
        )
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.post("/strategies/{strategy_id}/training-runs", response_model=TrainingRunRead, status_code=202, tags=["training"])
def create_training_run(
    strategy_id: str,
    request: TrainingRequest,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> TrainingRunRead:
    try:
        run = use_cases.start_training(
            TrainingCommand(
                strategy_id=strategy_id,
                auto_validate=request.auto_validate,
                overrides={
                    "exchange_id": request.exchange_id,
                    "data_mode": request.data_mode,
                    "sentiment_required": request.sentiment_required,
                    "symbol": request.symbol,
                    "sentiment_symbol": request.sentiment_symbol,
                    "timeframe": request.timeframe,
                    "target_n": request.target_n,
                    "take_profit_pct": request.take_profit_pct,
                    "stop_loss_pct": request.stop_loss_pct,
                    "training_rows": request.training_rows,
                },
            )
        )
        return _run_read(run)
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.get("/training-runs/{run_id}", response_model=TrainingRunRead, tags=["training"])
def get_training_run(run_id: str, use_cases: TrainingUseCases = Depends(get_use_cases)) -> TrainingRunRead:
    try:
        return _run_read(use_cases.get_run(run_id))
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.get("/strategies/{strategy_id}/models", response_model=list[TrainedModelSummary], tags=["models"])
def list_strategy_models(
    strategy_id: str,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> list[TrainedModelSummary]:
    try:
        return [_model_summary(model) for model in use_cases.list_models_for_strategy(strategy_id)]
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.get("/models/{model_id}", response_model=TrainedModelDetail, tags=["models"])
def get_model(model_id: str, use_cases: TrainingUseCases = Depends(get_use_cases)) -> TrainedModelDetail:
    try:
        return _model_detail(use_cases.get_model(model_id))
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.post("/models/{model_id}/validate", response_model=TrainedModelDetail, tags=["validation"])
def validate_trained_model(
    model_id: str,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> TrainedModelDetail:
    try:
        return _model_detail(use_cases.validate_model(model_id))
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.post("/models/{model_id}/approve", response_model=TrainedModelDetail, tags=["approval"])
def approve_trained_model(
    model_id: str,
    request: ApprovalRequest,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> TrainedModelDetail:
    try:
        return _model_detail(use_cases.approve_model(DecisionCommand(model_id, request.operator, request.comments)))
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.post("/models/{model_id}/reject", response_model=TrainedModelDetail, tags=["approval"])
def reject_trained_model(
    model_id: str,
    request: ApprovalRequest,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> TrainedModelDetail:
    try:
        return _model_detail(use_cases.reject_model(DecisionCommand(model_id, request.operator, request.comments)))
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.delete("/models/{model_id}", response_model=DeletedModelRead, tags=["models"])
def delete_rejected_model(
    model_id: str,
    request: DeleteModelRequest,
    use_cases: TrainingUseCases = Depends(get_use_cases),
) -> DeletedModelRead:
    try:
        result = use_cases.delete_rejected_model(
            DeleteModelCommand(
                model_id=model_id,
                operator=request.operator,
                confirmed=request.confirmed,
                comments=request.comments,
            )
        )
        return _deleted_model_read(result)
    except DomainError as exc:
        raise _http_error(exc) from exc


@router.get("/audit-events", response_model=list[AuditEventRead], tags=["audit"])
def list_audit_events(use_cases: TrainingUseCases = Depends(get_use_cases)) -> list[AuditEventRead]:
    return [_audit_read(event) for event in use_cases.list_audit_events()]


def _strategy_summary(strategy: TrainingStrategy) -> StrategySummary:
    return StrategySummary(
        id=strategy.id,
        name=strategy.name,
        version=strategy.version,
        description=strategy.description,
        model_family=strategy.model_family,
        status=strategy.status.value,
    )


def _run_read(run: TrainingRun) -> TrainingRunRead:
    return TrainingRunRead(
        id=run.id,
        strategy_id=run.strategy_id,
        strategy_version=run.strategy_version,
        status=run.status.value,
        requested_parameters=run.requested_parameters,
        window_configuration=run.window_configuration,
        started_at=run.started_at,
        finished_at=run.finished_at,
        failure_reason=run.failure_reason,
        created_at=run.created_at,
        model_id=run.model_id,
        auto_validate=run.auto_validate,
        progress_phase=run.progress_phase,
        progress_pct=run.progress_pct,
        progress_message=run.progress_message,
        worker_id=run.worker_id,
        locked_at=run.locked_at,
        heartbeat_at=run.heartbeat_at,
    )


def _model_summary(model: TrainedModel) -> TrainedModelSummary:
    return TrainedModelSummary(
        id=model.id,
        run_id=model.run_id,
        strategy_id=model.strategy_id,
        strategy_version=model.strategy_version,
        status=model.status.value,
        artifact_format=model.artifact_format,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_detail(model: TrainedModel) -> TrainedModelDetail:
    return TrainedModelDetail(
        **_model_summary(model).model_dump(),
        artifact_path=model.artifact_path,
        dataset_metadata=model.feature_schema.get("dataset", {}),
        feature_schema=model.feature_schema,
        target_parameters=model.target_parameters,
        training_metrics=model.training_metrics,
        validation_summary=model.validation_summary,
        validation_results=[_validation_read(result) for result in model.validation_results],
    )


def _deleted_model_read(result: DeletedModelResult) -> DeletedModelRead:
    return DeletedModelRead(
        model_id=result.model_id,
        run_id=result.run_id,
        strategy_id=result.strategy_id,
        previous_status=result.previous_status.value,
        status="DELETED_FROM_OPERATIONAL_VIEWS",
        artifact_cleanup={
            "artifact_path": result.artifact_cleanup.artifact_path,
            "artifact_deleted": result.artifact_cleanup.artifact_deleted,
            "dataset_path": result.artifact_cleanup.dataset_path,
            "dataset_deleted": result.artifact_cleanup.dataset_deleted,
        },
    )


def _validation_read(result: ValidationResult) -> ValidationResultRead:
    return ValidationResultRead(
        id=result.id,
        validation_type=result.validation_type,
        window_metadata=result.window_metadata,
        ml_metrics=result.ml_metrics,
        operational_metrics=result.operational_metrics,
        created_at=result.created_at,
    )


def _audit_read(event: AuditEvent) -> AuditEventRead:
    return AuditEventRead(
        id=event.id,
        event_type=event.event_type,
        message=event.message,
        payload=event.payload,
        created_at=event.created_at,
    )


def _http_error(exc: DomainError) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, InvalidStateTransitionError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))
