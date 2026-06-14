from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    BacktestTradeRecord,
    CandleFeatureRecord,
    CandleRecord,
    FeatureSchemaRecord,
    ModelRegistryRecord,
    ModelTrainingRunRecord,
    SelectedStrategyRecord,
    StrategyRegistryRecord,
    WalkForwardWindowRecord,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import ModelStatus, StrategyStatus


class ModelTrainingError(ValueError):
    pass


class ModelApprovalError(ValueError):
    pass


@dataclass(frozen=True)
class TrainingRow:
    opened_at: datetime
    open_time_ms: int
    close: float
    next_close: float
    values: dict[str, float]
    label: int


class TrainedBinaryModel(Protocol):
    model_type: str
    parameters: dict

    def predict_probabilities(
        self, rows: list[TrainingRow], feature_names: list[str]
    ) -> list[float]:
        ...

    def save(self, artifact_path: Path) -> None:
        ...


class BinaryModelTrainer(Protocol):
    def fit(self, rows: list[TrainingRow], feature_names: list[str]) -> TrainedBinaryModel:
        ...


@dataclass(frozen=True)
class BacktestTrade:
    entry_at: datetime
    exit_at: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    trades: list[BacktestTrade]
    equity_curve: list[float]
    metrics: dict


class XGBoostBinaryModelTrainer:
    def fit(self, rows: list[TrainingRow], feature_names: list[str]) -> TrainedBinaryModel:
        labels = [row.label for row in rows]
        if len(set(labels)) < 2:
            raise ModelTrainingError(
                "Training rows must contain both positive and negative labels."
            )
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise ModelTrainingError(
                "XGBoost is not installed. Run with the backend training dependency group."
            ) from exc

        features = [[row.values[name] for name in feature_names] for row in rows]
        classifier = XGBClassifier(
            n_estimators=80,
            max_depth=3,
            learning_rate=0.08,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            random_state=42,
        )
        classifier.fit(features, labels)
        return XGBoostTrainedBinaryModel(classifier=classifier)


@dataclass
class XGBoostTrainedBinaryModel:
    classifier: object
    model_type: str = "xgboost.XGBClassifier"

    @property
    def parameters(self) -> dict:
        return self.classifier.get_params()

    def predict_probabilities(
        self, rows: list[TrainingRow], feature_names: list[str]
    ) -> list[float]:
        features = [[row.values[name] for name in feature_names] for row in rows]
        probabilities = self.classifier.predict_proba(features)
        return [float(row[1]) for row in probabilities]

    def save(self, artifact_path: Path) -> None:
        self.classifier.save_model(artifact_path)


def train_selected_strategy_models(
    session: Session,
    settings: Settings,
    *,
    trainer: BinaryModelTrainer | None = None,
) -> list[ModelRegistryRecord]:
    selected, strategy = _selected_strategy(session)
    feature_schema = _feature_schema_for_strategy(session, strategy)
    rows = _training_rows(session, settings, strategy, feature_schema)
    if len(rows) < settings.model_training_min_rows:
        raise ModelTrainingError(
            f"Need at least {settings.model_training_min_rows} feature rows for B5 training; "
            f"found {len(rows)}."
        )

    model_trainer = trainer or XGBoostBinaryModelTrainer()
    trained_models: list[ModelRegistryRecord] = []
    parameters = {**strategy.default_parameters, **selected.parameters}
    for role in strategy.model_roles:
        role_name = str(role["role"])
        trained_models.append(
            _train_role_model(
                session,
                settings,
                trainer=model_trainer,
                strategy=strategy,
                role_name=role_name,
                parameters=parameters,
                feature_schema=feature_schema,
                rows=rows,
            )
        )
    return trained_models


def approve_model(session: Session, settings: Settings, *, model_id: str) -> ModelRegistryRecord:
    model = session.scalar(
        select(ModelRegistryRecord).where(ModelRegistryRecord.model_id == model_id)
    )
    if model is None:
        raise ModelApprovalError("Model does not exist.")
    if model.status not in {ModelStatus.BACKTESTED.value, ModelStatus.VALIDATED.value}:
        raise ModelApprovalError("Only validated/backtested candidate models can be approved.")

    failures = artifact_failures(model) + approval_failures(model.metrics, settings)
    if failures:
        raise ModelApprovalError("; ".join(failures))

    model.status = ModelStatus.APPROVED.value
    model.approved_at = datetime.now(UTC)
    session.commit()
    session.refresh(model)
    return model


def approval_failures(metrics: dict, settings: Settings) -> list[str]:
    failures: list[str] = []
    if float(metrics.get("precision_class_1", 0.0)) < settings.model_min_precision_class_1:
        failures.append("precision_class_1 is below the approval threshold")
    if int(metrics.get("trade_count", 0)) < settings.model_min_trade_count:
        failures.append("trade_count is below the approval threshold")
    if float(metrics.get("profit_factor", 0.0)) < settings.model_min_profit_factor:
        failures.append("profit_factor is below the approval threshold")
    if (
        int(metrics.get("acceptable_walk_forward_windows", 0))
        < settings.model_min_acceptable_walk_forward_windows
    ):
        failures.append("acceptable_walk_forward_windows is below the approval threshold")
    return failures


def artifact_failures(model: ModelRegistryRecord) -> list[str]:
    failures: list[str] = []
    if not model.artifact_uri:
        return ["model artifact_uri is required for approval"]

    artifact_path = Path(model.artifact_uri)
    if not artifact_path.exists():
        failures.append("model artifact file does not exist")
    elif not artifact_path.is_file():
        failures.append("model artifact path is not a file")
    else:
        try:
            json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failures.append("model artifact file is not valid JSON")

    metadata_path = artifact_path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        failures.append("model artifact metadata file does not exist")
        return failures
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append("model artifact metadata file is not valid JSON")
        return failures

    expected_metadata = {
        "model_id": model.model_id,
        "model_role": model.model_role,
        "strategy_id": model.strategy_id,
        "strategy_version": model.strategy_version,
        "feature_schema_id": model.feature_schema_id,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            failures.append(f"model artifact metadata {key} does not match registry")
    return failures


def latest_training_runs(session: Session, limit: int = 20) -> list[ModelTrainingRunRecord]:
    return list(
        session.scalars(
            select(ModelTrainingRunRecord)
            .order_by(desc(ModelTrainingRunRecord.started_at))
            .limit(max(1, min(limit, 100)))
        )
    )


def walk_forward_windows_for_model(
    session: Session, model_id: str
) -> list[WalkForwardWindowRecord]:
    return list(
        session.scalars(
            select(WalkForwardWindowRecord)
            .where(WalkForwardWindowRecord.model_id == model_id)
            .order_by(WalkForwardWindowRecord.window_index)
        )
    )


def backtest_trades_for_model(session: Session, model_id: str) -> list[BacktestTradeRecord]:
    return list(
        session.scalars(
            select(BacktestTradeRecord)
            .where(BacktestTradeRecord.model_id == model_id)
            .order_by(BacktestTradeRecord.trade_index)
        )
    )


def _train_role_model(
    session: Session,
    settings: Settings,
    *,
    trainer: BinaryModelTrainer,
    strategy: StrategyRegistryRecord,
    role_name: str,
    parameters: dict,
    feature_schema: FeatureSchemaRecord,
    rows: list[TrainingRow],
) -> ModelRegistryRecord:
    model_id = _model_id(strategy, role_name)
    started_at = datetime.now(UTC)
    run = ModelTrainingRunRecord(
        model_id=model_id,
        model_role=role_name,
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.version,
        feature_schema_id=feature_schema.schema_id,
        status="RUNNING",
        started_at=started_at,
        training_rows=0,
        holdout_rows=0,
        metrics={},
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        train_rows, holdout_rows = _chronological_holdout(rows, settings)
        windows = _walk_forward_validation(
            train_rows,
            feature_names=list(strategy.required_features),
            trainer=trainer,
            settings=settings,
        )
        final_model = trainer.fit(train_rows, list(strategy.required_features))
        holdout_probabilities = final_model.predict_probabilities(
            holdout_rows, list(strategy.required_features)
        )
        backtest = _backtest_holdout(
            holdout_rows,
            holdout_probabilities,
            parameters=parameters,
            settings=settings,
        )
        precision = _precision_class_1(holdout_rows, holdout_probabilities)
        acceptable_windows = sum(1 for window in windows if window["acceptable"])
        metrics = {
            "precision_class_1": precision,
            "trade_count": backtest.metrics["trade_count"],
            "net_pnl": backtest.metrics["net_pnl"],
            "profit_factor": backtest.metrics["profit_factor"],
            "max_drawdown": backtest.metrics["max_drawdown"],
            "win_rate": backtest.metrics["win_rate"],
            "max_losing_streak": backtest.metrics["max_losing_streak"],
            "acceptable_walk_forward_windows": acceptable_windows,
            "walk_forward_windows": windows,
            "holdout_start": holdout_rows[0].opened_at.isoformat(),
            "holdout_end": holdout_rows[-1].opened_at.isoformat(),
            "approval_failures": [],
        }
        artifact_uri = _persist_artifact(
            settings,
            model_id=model_id,
            model=final_model,
            metadata={
                "model_id": model_id,
                "model_role": role_name,
                "strategy_id": strategy.strategy_id,
                "strategy_version": strategy.version,
                "feature_schema_id": feature_schema.schema_id,
                "features": strategy.required_features,
                "metrics": metrics,
            },
        )
        model_record = ModelRegistryRecord(
            model_id=model_id,
            model_role=role_name,
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
            asset_symbol=settings.symbol,
            timeframe=settings.timeframe,
            feature_schema_id=feature_schema.schema_id,
            status=ModelStatus.BACKTESTED.value,
            artifact_uri=artifact_uri,
            metrics=metrics | {"approval_failures": approval_failures(metrics, settings)},
            parameters={
                "strategy_parameters": parameters,
                "model_parameters": final_model.parameters,
                "model_type": final_model.model_type,
            },
            training_window_start=train_rows[0].opened_at,
            training_window_end=train_rows[-1].opened_at,
            holdout_start=holdout_rows[0].opened_at,
            holdout_end=holdout_rows[-1].opened_at,
        )
        session.add(model_record)
        _replace_window_records(session, model_id, windows)
        _replace_backtest_trade_records(session, model_id, backtest.trades)
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        run.training_rows = len(train_rows)
        run.holdout_rows = len(holdout_rows)
        run.metrics = model_record.metrics
        session.commit()
        session.refresh(model_record)
        return model_record
    except Exception as exc:
        run.status = "FAILED"
        run.completed_at = datetime.now(UTC)
        run.error_message = str(exc)
        session.commit()
        raise


def _selected_strategy(session: Session) -> tuple[SelectedStrategyRecord, StrategyRegistryRecord]:
    selected = session.scalar(
        select(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == StrategyStatus.SELECTED.value)
        .order_by(desc(SelectedStrategyRecord.selected_at))
        .limit(1)
    )
    if selected is None:
        raise ModelTrainingError("No selected strategy.")
    strategy = session.get(StrategyRegistryRecord, selected.strategy_registry_id)
    if strategy is None:
        raise ModelTrainingError("Selected strategy registry record is missing.")
    if not strategy.model_roles:
        raise ModelTrainingError("Selected strategy does not declare model roles.")
    return selected, strategy


def _feature_schema_for_strategy(
    session: Session, strategy: StrategyRegistryRecord
) -> FeatureSchemaRecord:
    required = set(strategy.required_features)
    schemas = list(
        session.scalars(select(FeatureSchemaRecord).order_by(desc(FeatureSchemaRecord.id)))
    )
    for schema in schemas:
        if required.issubset(set(schema.features)):
            return schema
    raise ModelTrainingError("No feature schema satisfies the selected strategy requirements.")


def _training_rows(
    session: Session,
    settings: Settings,
    strategy: StrategyRegistryRecord,
    feature_schema: FeatureSchemaRecord,
) -> list[TrainingRow]:
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
    candle_by_time = {candle.open_time_ms: candle for candle in candles}
    features = list(
        session.scalars(
            select(CandleFeatureRecord)
            .where(
                CandleFeatureRecord.exchange == settings.exchange,
                CandleFeatureRecord.symbol == settings.symbol,
                CandleFeatureRecord.timeframe == settings.timeframe,
                CandleFeatureRecord.feature_schema_id == feature_schema.schema_id,
            )
            .order_by(CandleFeatureRecord.open_time_ms)
        )
    )
    feature_times = [
        feature.open_time_ms
        for feature in features
        if feature.open_time_ms in candle_by_time
    ]
    next_candle_by_time = {
        current: candle_by_time[next_time]
        for current, next_time in zip(feature_times, feature_times[1:], strict=False)
        if next_time in candle_by_time
    }
    rows: list[TrainingRow] = []
    required_features = list(strategy.required_features)
    for feature in features:
        candle = candle_by_time.get(feature.open_time_ms)
        next_candle = next_candle_by_time.get(feature.open_time_ms)
        if candle is None or next_candle is None:
            continue
        try:
            values = {name: float(feature.values[name]) for name in required_features}
        except (KeyError, TypeError, ValueError):
            continue
        if any(not math.isfinite(value) for value in values.values()):
            continue
        close = float(candle.close)
        next_close = float(next_candle.close)
        rows.append(
            TrainingRow(
                opened_at=feature.candle_opened_at,
                open_time_ms=feature.open_time_ms,
                close=close,
                next_close=next_close,
                values=values,
                label=1 if next_close > close else 0,
            )
        )
    return rows


def _chronological_holdout(
    rows: list[TrainingRow], settings: Settings
) -> tuple[list[TrainingRow], list[TrainingRow]]:
    holdout_size = max(
        settings.model_holdout_min_rows,
        int(len(rows) * settings.model_holdout_fraction),
    )
    holdout_size = min(max(1, holdout_size), len(rows) - 2)
    train_rows = rows[:-holdout_size]
    holdout_rows = rows[-holdout_size:]
    if not train_rows or not holdout_rows:
        raise ModelTrainingError("Not enough rows for chronological holdout.")
    if train_rows[-1].open_time_ms >= holdout_rows[0].open_time_ms:
        raise ModelTrainingError("Chronological training/holdout split is invalid.")
    return train_rows, holdout_rows


def _walk_forward_validation(
    rows: list[TrainingRow],
    *,
    feature_names: list[str],
    trainer: BinaryModelTrainer,
    settings: Settings,
) -> list[dict]:
    windows: list[dict] = []
    window_count = max(1, settings.model_walk_forward_windows)
    validation_size = max(4, len(rows) // (window_count + 3))
    min_train_size = max(10, validation_size * 2)
    for index in range(window_count):
        train_end = min_train_size + index * validation_size
        validation_start = train_end
        validation_end = validation_start + validation_size
        if validation_end > len(rows):
            break
        train_rows = rows[:train_end]
        validation_rows = rows[validation_start:validation_end]
        model = trainer.fit(train_rows, feature_names)
        probabilities = model.predict_probabilities(validation_rows, feature_names)
        precision = _precision_class_1(validation_rows, probabilities)
        predicted_positive_count = sum(1 for probability in probabilities if probability >= 0.5)
        actual_positive_count = sum(row.label for row in validation_rows)
        acceptable = (
            precision >= settings.model_min_precision_class_1
            and predicted_positive_count > 0
        )
        windows.append(
            {
                "window_index": index + 1,
                "train_start": train_rows[0].opened_at.isoformat(),
                "train_end": train_rows[-1].opened_at.isoformat(),
                "validation_start": validation_rows[0].opened_at.isoformat(),
                "validation_end": validation_rows[-1].opened_at.isoformat(),
                "precision_class_1": precision,
                "predicted_positive_count": predicted_positive_count,
                "actual_positive_count": actual_positive_count,
                "acceptable": acceptable,
            }
        )
    if not windows:
        raise ModelTrainingError("Not enough rows for walk-forward validation.")
    return windows


def _precision_class_1(rows: list[TrainingRow], probabilities: list[float]) -> float:
    predicted_positive = [
        index for index, probability in enumerate(probabilities) if probability >= 0.5
    ]
    if not predicted_positive:
        return 0.0
    true_positive = sum(1 for index in predicted_positive if rows[index].label == 1)
    return round(true_positive / len(predicted_positive), 6)


def _backtest_holdout(
    rows: list[TrainingRow],
    probabilities: list[float],
    *,
    parameters: dict,
    settings: Settings,
) -> BacktestResult:
    cash = float(settings.initial_capital_usd)
    initial_cash = cash
    quantity = 0.0
    entry_price = 0.0
    entry_at: datetime | None = None
    trades: list[BacktestTrade] = []
    equity_curve: list[float] = [cash]
    min_probability = float(parameters.get("min_model_probability", 0.5))
    oversold_threshold = float(parameters.get("oversold_threshold", 30.0))
    stop_loss_pct = float(parameters.get("stop_loss_pct", 0.015))
    take_profit_pct = float(parameters.get("take_profit_pct", 0.03))
    fee_rate = settings.backtest_fee_rate
    slippage_rate = settings.backtest_slippage_rate

    for index, row in enumerate(rows):
        price = row.close
        if quantity == 0:
            if (
                row.values.get("rsi_14", 100.0) <= oversold_threshold
                and probabilities[index] >= min_probability
            ):
                entry_price = price * (1 + slippage_rate)
                entry_fee = cash * fee_rate
                quantity = (cash - entry_fee) / entry_price
                cash = 0.0
                entry_at = row.opened_at
        else:
            exit_reason = ""
            if price <= entry_price * (1 - stop_loss_pct):
                exit_reason = "STOP_LOSS"
            elif price >= entry_price * (1 + take_profit_pct):
                exit_reason = "TAKE_PROFIT"
            elif index == len(rows) - 1:
                exit_reason = "HOLDOUT_END"

            if exit_reason:
                exit_price = price * (1 - slippage_rate)
                gross = quantity * exit_price
                exit_fee = gross * fee_rate
                cash = gross - exit_fee
                entry_value = quantity * entry_price
                pnl = cash - entry_value
                trades.append(
                    BacktestTrade(
                        entry_at=entry_at or row.opened_at,
                        exit_at=row.opened_at,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=quantity,
                        pnl=pnl,
                        pnl_pct=pnl / entry_value if entry_value else 0.0,
                        exit_reason=exit_reason,
                    )
                )
                quantity = 0.0
                entry_price = 0.0
                entry_at = None
        equity_curve.append(cash if quantity == 0 else quantity * price)

    metrics = _backtest_metrics(trades, equity_curve, initial_cash)
    return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)


def _backtest_metrics(
    trades: list[BacktestTrade], equity_curve: list[float], initial_cash: float
) -> dict:
    pnl_values = [trade.pnl for trade in trades]
    gross_profit = sum(value for value in pnl_values if value > 0)
    gross_loss = abs(sum(value for value in pnl_values if value < 0))
    if gross_loss == 0:
        profit_factor = 999.0 if gross_profit > 0 else 0.0
    else:
        profit_factor = gross_profit / gross_loss
    wins = sum(1 for value in pnl_values if value > 0)
    max_losing_streak = 0
    current_losing_streak = 0
    for value in pnl_values:
        if value < 0:
            current_losing_streak += 1
            max_losing_streak = max(max_losing_streak, current_losing_streak)
        else:
            current_losing_streak = 0
    return {
        "trade_count": len(trades),
        "net_pnl": round((equity_curve[-1] if equity_curve else initial_cash) - initial_cash, 6),
        "profit_factor": round(profit_factor, 6),
        "max_drawdown": round(_max_drawdown(equity_curve), 6),
        "win_rate": round(wins / len(trades), 6) if trades else 0.0,
        "max_losing_streak": max_losing_streak,
    }


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 0.0
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown


def _replace_window_records(session: Session, model_id: str, windows: list[dict]) -> None:
    session.execute(
        delete(WalkForwardWindowRecord).where(WalkForwardWindowRecord.model_id == model_id)
    )
    for window in windows:
        session.add(
            WalkForwardWindowRecord(
                model_id=model_id,
                window_index=window["window_index"],
                train_start=datetime.fromisoformat(window["train_start"]),
                train_end=datetime.fromisoformat(window["train_end"]),
                validation_start=datetime.fromisoformat(window["validation_start"]),
                validation_end=datetime.fromisoformat(window["validation_end"]),
                precision_class_1=Decimal(str(window["precision_class_1"])),
                predicted_positive_count=window["predicted_positive_count"],
                actual_positive_count=window["actual_positive_count"],
                acceptable=window["acceptable"],
                metrics=window,
            )
        )


def _replace_backtest_trade_records(
    session: Session, model_id: str, trades: list[BacktestTrade]
) -> None:
    session.execute(delete(BacktestTradeRecord).where(BacktestTradeRecord.model_id == model_id))
    for index, trade in enumerate(trades, start=1):
        session.add(
            BacktestTradeRecord(
                model_id=model_id,
                trade_index=index,
                entry_at=trade.entry_at,
                exit_at=trade.exit_at,
                entry_price=Decimal(str(trade.entry_price)),
                exit_price=Decimal(str(trade.exit_price)),
                quantity=Decimal(str(trade.quantity)),
                pnl=Decimal(str(trade.pnl)),
                pnl_pct=Decimal(str(trade.pnl_pct)),
                exit_reason=trade.exit_reason,
            )
        )


def _persist_artifact(
    settings: Settings, *, model_id: str, model: TrainedBinaryModel, metadata: dict
) -> str:
    artifact_dir = Path(settings.model_artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_model_id = _safe_identifier(model_id)
    model_path = artifact_dir / f"{safe_model_id}.json"
    metadata_path = artifact_dir / f"{safe_model_id}.metadata.json"
    model.save(model_path)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return str(model_path)


def _model_id(strategy: StrategyRegistryRecord, role_name: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{strategy.strategy_id}:{strategy.version}:{role_name}:{timestamp}"


def _safe_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
