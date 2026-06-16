from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from smart_trade.domain.entities import ApprovalRecord, AuditEvent, TrainedModel, TrainingRun, TrainingStrategy, ValidationResult
from smart_trade.domain.enums import ApprovalDecision, StrategyStatus, TrainedModelStatus, TrainingRunStatus
from smart_trade.adapters.persistence.models import (
    AuditEventRecord,
    TrainedModelRecord,
    TrainingApprovalDecisionRecord,
    TrainingRunRecord,
    TrainingStrategyRecord,
    TrainingValidationResultRecord,
)


class SqlAlchemyStrategyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[TrainingStrategy]:
        records = self.session.execute(select(TrainingStrategyRecord).order_by(TrainingStrategyRecord.name)).scalars().all()
        return [_strategy_from_record(record) for record in records]

    def get(self, strategy_id: str) -> TrainingStrategy | None:
        record = self.session.get(TrainingStrategyRecord, strategy_id)
        return _strategy_from_record(record) if record else None

    def save(self, strategy: TrainingStrategy) -> None:
        record = self.session.get(TrainingStrategyRecord, strategy.id)
        payload = {
            "id": strategy.id,
            "name": strategy.name,
            "version": strategy.version,
            "description": strategy.description,
            "model_family": strategy.model_family,
            "status": strategy.status.value,
            "feature_contract": strategy.feature_contract,
            "default_parameters": strategy.default_parameters,
        }
        if record is None:
            self.session.add(TrainingStrategyRecord(**payload))
        else:
            for key, value in payload.items():
                setattr(record, key, value)
        self.session.commit()


class SqlAlchemyTrainingRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: str) -> TrainingRun | None:
        record = self.session.get(TrainingRunRecord, run_id)
        return _run_from_record(record) if record else None

    def claim_next_pending(self, worker_id: str, timestamp: datetime) -> TrainingRun | None:
        record = self.session.execute(
            select(TrainingRunRecord)
            .where(TrainingRunRecord.status == TrainingRunStatus.PENDING.value)
            .order_by(TrainingRunRecord.created_at)
            .limit(1)
        ).scalar_one_or_none()
        if record is None:
            return None

        run = _run_from_record(record)
        run.mark_running(timestamp, worker_id)
        self._apply_run(record, run)
        self.session.commit()
        return run

    def save(self, run: TrainingRun) -> None:
        record = self.session.get(TrainingRunRecord, run.id)
        payload = {
            "id": run.id,
            "strategy_id": run.strategy_id,
            "strategy_version": run.strategy_version,
            "status": run.status.value,
            "requested_parameters": run.requested_parameters,
            "window_configuration": run.window_configuration,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "failure_reason": run.failure_reason,
            "auto_validate": run.auto_validate,
            "progress_phase": run.progress_phase,
            "progress_pct": run.progress_pct,
            "progress_message": run.progress_message,
            "worker_id": run.worker_id,
            "locked_at": run.locked_at,
            "heartbeat_at": run.heartbeat_at,
        }
        if record is None:
            self.session.add(TrainingRunRecord(**payload))
        else:
            self._apply_run(record, run)
        self.session.commit()

    @staticmethod
    def _apply_run(record: TrainingRunRecord, run: TrainingRun) -> None:
        payload = {
            "strategy_id": run.strategy_id,
            "strategy_version": run.strategy_version,
            "status": run.status.value,
            "requested_parameters": run.requested_parameters,
            "window_configuration": run.window_configuration,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "failure_reason": run.failure_reason,
            "auto_validate": run.auto_validate,
            "progress_phase": run.progress_phase,
            "progress_pct": run.progress_pct,
            "progress_message": run.progress_message,
            "worker_id": run.worker_id,
            "locked_at": run.locked_at,
            "heartbeat_at": run.heartbeat_at,
        }
        for key, value in payload.items():
            setattr(record, key, value)


class SqlAlchemyTrainedModelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, model_id: str) -> TrainedModel | None:
        record = self.session.get(TrainedModelRecord, model_id)
        return _model_from_record(record) if record else None

    def get_by_run_id(self, run_id: str) -> TrainedModel | None:
        record = self.session.execute(select(TrainedModelRecord).where(TrainedModelRecord.run_id == run_id)).scalar_one_or_none()
        return _model_from_record(record) if record else None

    def list_by_strategy(self, strategy_id: str) -> list[TrainedModel]:
        records = self.session.execute(
            select(TrainedModelRecord).where(TrainedModelRecord.strategy_id == strategy_id).order_by(desc(TrainedModelRecord.created_at))
        ).scalars().all()
        return [_model_from_record(record) for record in records]

    def save(self, model: TrainedModel) -> None:
        record = self.session.get(TrainedModelRecord, model.id)
        payload = {
            "id": model.id,
            "run_id": model.run_id,
            "strategy_id": model.strategy_id,
            "strategy_version": model.strategy_version,
            "status": model.status.value,
            "artifact_path": model.artifact_path,
            "artifact_format": model.artifact_format,
            "feature_schema": model.feature_schema,
            "target_parameters": model.target_parameters,
            "training_metrics": model.training_metrics,
            "validation_summary": model.validation_summary,
            "updated_at": model.updated_at,
        }
        if record is None:
            self.session.add(TrainedModelRecord(**payload, created_at=model.created_at))
        else:
            for key, value in payload.items():
                setattr(record, key, value)
        self.session.commit()

    def delete(self, model_id: str) -> None:
        record = self.session.get(TrainedModelRecord, model_id)
        if record is None:
            return
        self.session.delete(record)
        self.session.commit()


class SqlAlchemyValidationResultRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, result: ValidationResult) -> None:
        self.session.add(
            TrainingValidationResultRecord(
                id=result.id,
                model_id=result.model_id,
                validation_type=result.validation_type,
                window_metadata=result.window_metadata,
                ml_metrics=result.ml_metrics,
                operational_metrics=result.operational_metrics,
                created_at=result.created_at,
            )
        )
        self.session.commit()


class SqlAlchemyApprovalDecisionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, decision: ApprovalRecord) -> None:
        self.session.add(
            TrainingApprovalDecisionRecord(
                id=decision.id,
                model_id=decision.model_id,
                decision=decision.decision.value,
                operator=decision.operator,
                comments=decision.comments,
                created_at=decision.created_at,
            )
        )
        self.session.commit()


class SqlAlchemyAuditEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        records = self.session.execute(select(AuditEventRecord).order_by(desc(AuditEventRecord.created_at)).limit(limit)).scalars().all()
        return [_audit_from_record(record) for record in records]

    def save(self, event: AuditEvent) -> None:
        self.session.add(
            AuditEventRecord(
                id=event.id,
                event_type=event.event_type,
                message=event.message,
                payload=event.payload,
                created_at=event.created_at,
            )
        )
        self.session.commit()


def _strategy_from_record(record: TrainingStrategyRecord) -> TrainingStrategy:
    return TrainingStrategy(
        id=record.id,
        name=record.name,
        version=record.version,
        description=record.description,
        model_family=record.model_family,
        status=StrategyStatus(record.status),
        feature_contract=record.feature_contract,
        default_parameters=record.default_parameters,
    )


def _run_from_record(record: TrainingRunRecord) -> TrainingRun:
    return TrainingRun(
        id=record.id,
        strategy_id=record.strategy_id,
        strategy_version=record.strategy_version,
        status=TrainingRunStatus(record.status),
        requested_parameters=record.requested_parameters,
        window_configuration=record.window_configuration,
        started_at=record.started_at,
        finished_at=record.finished_at,
        failure_reason=record.failure_reason,
        created_at=record.created_at,
        model_id=record.model.id if record.model else None,
        auto_validate=record.auto_validate,
        progress_phase=record.progress_phase,
        progress_pct=record.progress_pct,
        progress_message=record.progress_message,
        worker_id=record.worker_id,
        locked_at=record.locked_at,
        heartbeat_at=record.heartbeat_at,
    )


def _model_from_record(record: TrainedModelRecord) -> TrainedModel:
    return TrainedModel(
        id=record.id,
        run_id=record.run_id,
        strategy_id=record.strategy_id,
        strategy_version=record.strategy_version,
        status=TrainedModelStatus(record.status),
        artifact_path=record.artifact_path,
        artifact_format=record.artifact_format,
        feature_schema=record.feature_schema,
        target_parameters=record.target_parameters,
        training_metrics=record.training_metrics,
        validation_summary=record.validation_summary,
        created_at=record.created_at,
        updated_at=record.updated_at,
        validation_results=[_validation_from_record(result) for result in record.validation_results],
        approval_decisions=[_decision_from_record(decision) for decision in record.approval_decisions],
    )


def _validation_from_record(record: TrainingValidationResultRecord) -> ValidationResult:
    return ValidationResult(
        id=record.id,
        model_id=record.model_id,
        validation_type=record.validation_type,
        window_metadata=record.window_metadata,
        ml_metrics=record.ml_metrics,
        operational_metrics=record.operational_metrics,
        created_at=record.created_at,
    )


def _decision_from_record(record: TrainingApprovalDecisionRecord) -> ApprovalRecord:
    return ApprovalRecord(
        id=record.id,
        model_id=record.model_id,
        decision=ApprovalDecision(record.decision),
        operator=record.operator,
        comments=record.comments,
        created_at=record.created_at,
    )


def _audit_from_record(record: AuditEventRecord) -> AuditEvent:
    return AuditEvent(
        id=record.id,
        event_type=record.event_type,
        message=record.message,
        payload=record.payload,
        created_at=record.created_at,
    )
