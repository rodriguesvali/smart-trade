from __future__ import annotations

from sqlalchemy.orm import Session

from smart_trade.adapters.market_data.ccxt_market_data_provider import CcxtMarketDataProvider
from smart_trade.adapters.market_data.ccxt_sentiment_data_provider import CcxtSentimentDataProvider
from smart_trade.adapters.ml.xgboost_training_adapter import RealXGBoostTrainingAdapter, SyntheticXGBoostTrainingAdapter
from smart_trade.adapters.persistence.sqlalchemy_repositories import (
    SqlAlchemyApprovalDecisionRepository,
    SqlAlchemyAuditEventRepository,
    SqlAlchemyStrategyRepository,
    SqlAlchemyTrainedModelRepository,
    SqlAlchemyTrainingRunRepository,
    SqlAlchemyValidationResultRepository,
)
from smart_trade.application.use_cases.training import TrainingUseCases
from smart_trade.infrastructure.clock import SystemClock, UuidGenerator
from smart_trade.infrastructure.config import get_settings


def build_training_use_cases(session: Session) -> TrainingUseCases:
    settings = get_settings()
    strategy_repo = SqlAlchemyStrategyRepository(session)
    run_repo = SqlAlchemyTrainingRunRepository(session)
    model_repo = SqlAlchemyTrainedModelRepository(session)
    validation_repo = SqlAlchemyValidationResultRepository(session)
    decision_repo = SqlAlchemyApprovalDecisionRepository(session)
    audit_repo = SqlAlchemyAuditEventRepository(session)
    if settings.data_mode == "synthetic":
        ml_adapter = SyntheticXGBoostTrainingAdapter(settings.artifact_dir, settings.global_random_seed)
    else:
        ml_adapter = RealXGBoostTrainingAdapter(
            settings.artifact_dir,
            settings.global_random_seed,
            CcxtMarketDataProvider(),
            CcxtSentimentDataProvider(),
        )
    return TrainingUseCases(
        strategies=strategy_repo,
        runs=run_repo,
        models=model_repo,
        validations=validation_repo,
        decisions=decision_repo,
        audit_events=audit_repo,
        trainer=ml_adapter,
        validator=ml_adapter,
        clock=SystemClock(),
        ids=UuidGenerator(),
    )
