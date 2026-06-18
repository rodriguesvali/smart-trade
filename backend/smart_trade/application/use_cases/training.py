from __future__ import annotations

from dataclasses import dataclass

from smart_trade.application.ports.clock import Clock, IdGenerator
from smart_trade.application.ports.ml import ArtifactDeletionResult, ModelArtifactStore, ModelTrainer, ModelValidator
from smart_trade.application.ports.repositories import (
    ApprovalDecisionRepository,
    AuditEventRepository,
    StrategyRepository,
    TrainedModelRepository,
    TrainingRunRepository,
    ValidationResultRepository,
)
from smart_trade.domain.entities import ApprovalRecord, AuditEvent, TrainedModel, TrainingRun, ValidationResult
from smart_trade.domain.enums import ApprovalDecision, TrainedModelStatus, TrainingRunStatus
from smart_trade.domain.exceptions import InvalidStateTransitionError, NotFoundError, ValidationError
from smart_trade.domain.training_window import calculate_training_window


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


@dataclass(frozen=True)
class DeleteModelCommand:
    model_id: str
    operator: str
    confirmed: bool
    comments: str | None


@dataclass(frozen=True)
class DeletedModelResult:
    model_id: str
    run_id: str
    strategy_id: str
    previous_status: TrainedModelStatus
    artifact_cleanup: ArtifactDeletionResult


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
        artifact_store: ModelArtifactStore,
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
        self.artifact_store = artifact_store
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
        parameters = _resolve_training_window_parameters(parameters)
        _validate_training_parameters(parameters)
        run = TrainingRun(
            id=self.ids.new_id(),
            strategy_id=strategy.id,
            strategy_version=strategy.version,
            status=TrainingRunStatus.PENDING,
            requested_parameters=parameters,
            window_configuration={
                "split": "chronological",
                "partitions": ["train", "validation_internal", "holdout"],
                "policy": parameters["training_window_policy"],
            },
            created_at=self.clock.now(),
            auto_validate=command.auto_validate,
            progress_phase="pending",
            progress_pct=0.0,
            progress_message="Training run is waiting for a worker",
        )
        self.runs.save(run)
        self._audit("TRAINING_REQUESTED", "Training run requested", {"run_id": run.id, "strategy_id": strategy.id})
        return run

    def execute_next_training(self, worker_id: str) -> TrainingRun | None:
        run = self.runs.claim_next_pending(worker_id, self.clock.now())
        if run is None:
            return None
        try:
            self._execute_training(run.id, worker_id)
            trained_run = self.get_run(run.id)
            if trained_run.auto_validate and trained_run.model_id is not None:
                self.validate_model(trained_run.model_id)
            return self.get_run(run.id)
        except Exception as exc:
            failed = self.get_run(run.id)
            failed.mark_failed(self.clock.now(), str(exc))
            self.runs.save(failed)
            self._audit("TRAINING_FAILED", "Training run failed", {"run_id": run.id, "error": str(exc)})
            raise

    def _execute_training(self, run_id: str, worker_id: str | None = None) -> None:
        run = self.get_run(run_id)
        if run.status == TrainingRunStatus.PENDING:
            run.mark_running(self.clock.now(), worker_id)
        if run.status != TrainingRunStatus.RUNNING:
            raise ValidationError("Training run is not available for execution")
        run.update_progress(self.clock.now(), "training_model", 0.20, "Building dataset and training model")
        self.runs.save(run)
        self._audit("TRAINING_STARTED", "Training run started", {"run_id": run.id})

        model_id = self.ids.new_id()
        output = self.trainer.train(model_id=model_id, parameters=run.requested_parameters)
        run.update_progress(self.clock.now(), "saving_model", 0.85, "Persisting trained model metadata")
        self.runs.save(run)
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

    def validate_model(self, model_id: str, validation_overrides: dict | None = None) -> TrainedModel:
        model = self.get_model(model_id)
        run = self.get_run(model.run_id)
        model.start_validation(self.clock.now())
        self.models.save(model)
        self._audit("VALIDATION_STARTED", "Model validation started", {"model_id": model.id})

        try:
            validation_parameters = _resolve_validation_parameters(run.requested_parameters, validation_overrides or {})
            _validate_validation_parameters(validation_parameters)
            output = self.validator.validate(artifact_path=model.artifact_path, parameters=validation_parameters)
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
            self._audit(
                "VALIDATION_COMPLETED",
                "Model validation completed",
                {"model_id": model.id, "validation_overrides": validation_overrides or {}},
            )
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

    def delete_rejected_model(self, command: DeleteModelCommand) -> DeletedModelResult:
        if not command.confirmed:
            raise ValidationError("Rejected model deletion requires explicit confirmation")

        model = self.get_model(command.model_id)
        if model.status != TrainedModelStatus.REJECTED:
            raise InvalidStateTransitionError("Only REJECTED models can be deleted")

        try:
            artifact_cleanup = self.artifact_store.delete(model.artifact_path)
        except OSError as exc:
            self._audit(
                "MODEL_DELETE_FAILED",
                "Rejected model artifact cleanup failed",
                {
                    "model_id": model.id,
                    "run_id": model.run_id,
                    "strategy_id": model.strategy_id,
                    "previous_status": model.status.value,
                    "artifact_path": model.artifact_path,
                    "operator": command.operator,
                    "comments": command.comments,
                    "error": str(exc),
                },
            )
            raise ValidationError(f"Rejected model artifact cleanup failed: {exc}") from exc

        result = DeletedModelResult(
            model_id=model.id,
            run_id=model.run_id,
            strategy_id=model.strategy_id,
            previous_status=model.status,
            artifact_cleanup=artifact_cleanup,
        )
        self.models.delete(model.id)
        self._audit(
            "MODEL_DELETED",
            "Rejected model deleted from operational views",
            {
                "model_id": model.id,
                "run_id": model.run_id,
                "strategy_id": model.strategy_id,
                "previous_status": model.status.value,
                "artifact_path": model.artifact_path,
                "operator": command.operator,
                "comments": command.comments,
                "artifact_cleanup": {
                    "artifact_path": artifact_cleanup.artifact_path,
                    "artifact_deleted": artifact_cleanup.artifact_deleted,
                    "dataset_path": artifact_cleanup.dataset_path,
                    "dataset_deleted": artifact_cleanup.dataset_deleted,
                },
            },
        )
        return result

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


def _validate_training_parameters(parameters: dict) -> None:
    for key in ("take_profit_pct", "stop_loss_pct", "trailing_activation_pct", "trailing_distance_pct"):
        if key not in parameters or parameters[key] is None:
            continue
        value = float(parameters[key])
        if value <= 0:
            raise ValidationError(f"{key} must be greater than zero")
        if value >= 1:
            raise ValidationError(
                f"{key} must be a decimal fraction, not a whole percent. Use 0.01 for 1%, 0.001 for 0.1%."
            )
    if float(parameters["validation_ratio"]) <= 0:
        raise ValidationError("validation_ratio must be greater than zero")
    if float(parameters["validation_ratio"]) + float(parameters["holdout_ratio"]) >= 1:
        raise ValidationError("validation_ratio plus holdout_ratio must leave a non-empty training partition")


def _validate_validation_parameters(parameters: dict) -> None:
    for key in ("take_profit_pct", "stop_loss_pct", "trailing_activation_pct", "trailing_distance_pct"):
        if key not in parameters or parameters[key] is None:
            continue
        value = float(parameters[key])
        if value <= 0:
            raise ValidationError(f"{key} must be greater than zero")
        if value >= 1:
            raise ValidationError(
                f"{key} must be a decimal fraction, not a whole percent. Use 0.01 for 1%, 0.001 for 0.1%."
            )
    for key in ("fee_pct", "slippage_pct"):
        if key in parameters and parameters[key] is not None and float(parameters[key]) < 0:
            raise ValidationError(f"{key} cannot be negative")
    if "rsi_oversold_threshold" in parameters and parameters["rsi_oversold_threshold"] is not None:
        value = float(parameters["rsi_oversold_threshold"])
        if value < 0 or value > 100:
            raise ValidationError("rsi_oversold_threshold must be between 0 and 100")


def _resolve_validation_parameters(training_parameters: dict, validation_overrides: dict) -> dict:
    resolved = dict(training_parameters)
    defaults = training_parameters.get("validation", {})
    if isinstance(defaults, dict):
        resolved.update({key: value for key, value in defaults.items() if value is not None})
    resolved["entry_rsi_threshold"] = resolved.get(
        "entry_rsi_threshold",
        resolved.get("rsi_oversold_threshold", 30.0),
    )
    for key, value in validation_overrides.items():
        if value is None:
            continue
        resolved[key] = value
        if key == "rsi_oversold_threshold":
            resolved["entry_rsi_threshold"] = value
    return resolved


def _resolve_training_window_parameters(parameters: dict) -> dict:
    target_n = int(parameters["target_n"])
    policy = calculate_training_window(str(parameters["timeframe"]), target_n)

    resolved = dict(parameters)
    original_training_rows = parameters.get("training_rows")
    original_holdout_ratio = parameters.get("holdout_ratio")
    resolved["training_rows"] = policy["usable_rows"]
    resolved["holdout_ratio"] = policy["holdout_ratio"]
    resolved["feature_warmup_rows"] = policy["feature_warmup_rows"]
    resolved["training_window_policy"] = policy | {
        "ignored_request_overrides": {
            "training_rows": original_training_rows,
            "holdout_ratio": original_holdout_ratio,
        }
    }
    return resolved
