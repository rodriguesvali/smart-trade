from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clock import Clock, IdGenerator
from app.application.ports.ml import ModelTrainer, ModelValidator
from app.application.ports.repositories import (
    ApprovalDecisionRepository,
    AuditEventRepository,
    StrategyRepository,
    TrainedModelRepository,
    TrainingRunRepository,
    ValidationResultRepository,
)
from app.domain.entities import ApprovalRecord, AuditEvent, TrainedModel, TrainingRun, ValidationResult
from app.domain.enums import ApprovalDecision, TrainedModelStatus, TrainingRunStatus
from app.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class TrainingCommand:
    strategy_id: str
    auto_validate: bool
    overrides: dict


@dataclass(frozen=True)
class DecisionCommand:
    model_id: str
    operator: str
    comments: str | None


class TrainingUseCases:
    def __init__(
        self,
        *,
        strategies: StrategyRepository,
        runs: TrainingRunRepository,
        models: TrainedModelRepository,
        validations: ValidationResultRepository,
        decisions: ApprovalDecisionRepository,
        audit_events: AuditEventRepository,
        trainer: ModelTrainer,
        validator: ModelValidator,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self.strategies = strategies
        self.runs = runs
        self.models = models
        self.validations = validations
        self.decisions = decisions
        self.audit_events = audit_events
        self.trainer = trainer
        self.validator = validator
        self.clock = clock
        self.ids = ids

    def list_strategies(self):
        return self.strategies.list()

    def get_strategy(self, strategy_id: str):
        strategy = self.strategies.get(strategy_id)
        if strategy is None:
            raise NotFoundError("Training strategy not found")
        return strategy

    def list_models_for_strategy(self, strategy_id: str):
        self.get_strategy(strategy_id)
        return self.models.list_by_strategy(strategy_id)

    def get_run(self, run_id: str) -> TrainingRun:
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError("Training run not found")
        return run

    def get_model(self, model_id: str) -> TrainedModel:
        model = self.models.get(model_id)
        if model is None:
            raise NotFoundError("Trained model not found")
        return model

    def start_training(self, command: TrainingCommand) -> TrainingRun:
        strategy = self.get_strategy(command.strategy_id)
        strategy.ensure_available()
        parameters = strategy.default_parameters | {k: v for k, v in command.overrides.items() if v is not None}
        run = TrainingRun(
            id=self.ids.new_id(),
            strategy_id=strategy.id,
            strategy_version=strategy.version,
            status=TrainingRunStatus.PENDING,
            requested_parameters=parameters,
            window_configuration={"split": "chronological", "partitions": ["train", "validation_internal", "holdout"]},
            created_at=self.clock.now(),
        )
        self.runs.save(run)
        self._audit("TRAINING_REQUESTED", "Training run requested", {"run_id": run.id, "strategy_id": strategy.id})

        try:
            self._execute_training(run.id)
            trained_run = self.get_run(run.id)
            if command.auto_validate and trained_run.model_id is not None:
                self.validate_model(trained_run.model_id)
            return self.get_run(run.id)
        except Exception as exc:
            failed = self.get_run(run.id)
            failed.mark_failed(self.clock.now(), str(exc))
            self.runs.save(failed)
            self._audit("TRAINING_FAILED", "Training run failed", {"run_id": run.id, "error": str(exc)})
            raise

    def _execute_training(self, run_id: str) -> None:
        run = self.get_run(run_id)
        run.mark_running(self.clock.now())
        self.runs.save(run)
        self._audit("TRAINING_STARTED", "Training run started", {"run_id": run.id})

        model_id = self.ids.new_id()
        output = self.trainer.train(model_id=model_id, parameters=run.requested_parameters)
        model = TrainedModel(
            id=model_id,
            run_id=run.id,
            strategy_id=run.strategy_id,
            strategy_version=run.strategy_version,
            status=TrainedModelStatus.TRAINED,
            artifact_path=output.artifact_path,
            artifact_format=output.artifact_format,
            feature_schema=output.feature_schema,
            target_parameters=output.target_parameters,
            training_metrics=output.training_metrics,
            created_at=self.clock.now(),
            updated_at=self.clock.now(),
        )
        self.models.save(model)
        run.mark_trained(self.clock.now(), model.id)
        self.runs.save(run)
        self._audit(
            "MODEL_TRAINED",
            "Training run completed and model artifact created",
            {"run_id": run.id, "model_id": model.id, "artifact_path": model.artifact_path},
        )

    def validate_model(self, model_id: str) -> TrainedModel:
        model = self.get_model(model_id)
        run = self.get_run(model.run_id)
        model.start_validation(self.clock.now())
        self.models.save(model)
        self._audit("VALIDATION_STARTED", "Model validation started", {"model_id": model.id})

        try:
            output = self.validator.validate(artifact_path=model.artifact_path, parameters=run.requested_parameters)
            result = ValidationResult(
                id=self.ids.new_id(),
                model_id=model.id,
                validation_type=output.validation_type,
                window_metadata=output.window_metadata,
                ml_metrics=output.ml_metrics,
                operational_metrics=output.operational_metrics,
                created_at=self.clock.now(),
            )
            self.validations.save(result)
            model.complete_validation(self.clock.now(), result)
            self.models.save(model)
            self._audit("VALIDATION_COMPLETED", "Model validation completed", {"model_id": model.id})
            return self.get_model(model.id)
        except Exception as exc:
            failed = self.get_model(model_id)
            failed.fail_validation(self.clock.now())
            self.models.save(failed)
            self._audit("VALIDATION_FAILED", "Model validation failed", {"model_id": model_id, "error": str(exc)})
            raise

    def approve_model(self, command: DecisionCommand) -> TrainedModel:
        return self._decide(command, ApprovalDecision.APPROVED)

    def reject_model(self, command: DecisionCommand) -> TrainedModel:
        return self._decide(command, ApprovalDecision.REJECTED)

    def _decide(self, command: DecisionCommand, decision: ApprovalDecision) -> TrainedModel:
        model = self.get_model(command.model_id)
        record = ApprovalRecord(
            id=self.ids.new_id(),
            model_id=model.id,
            decision=decision,
            operator=command.operator,
            comments=command.comments,
            created_at=self.clock.now(),
        )
        model.decide(self.clock.now(), decision, record)
        self.decisions.save(record)
        self.models.save(model)
        self._audit(f"MODEL_{decision.value}", f"Model {decision.value.lower()} by operator", {"model_id": model.id})
        return self.get_model(model.id)

    def list_audit_events(self):
        return self.audit_events.list_recent()

    def _audit(self, event_type: str, message: str, payload: dict) -> None:
        self.audit_events.save(
            AuditEvent(
                id=self.ids.new_id(),
                event_type=event_type,
                message=message,
                payload=payload,
                created_at=self.clock.now(),
            )
        )

