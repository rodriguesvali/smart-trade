from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import CommandRequestRecord
from smart_trade_backend.application.live.execution import LiveExecutionError, execute_live_order
from smart_trade_backend.application.model_training.service import (
    ModelApprovalError,
    approve_model,
)
from smart_trade_backend.application.paper.runtime import PaperRuntimeError, run_paper_replay
from smart_trade_backend.application.readiness.live import (
    LiveReadinessError,
    enable_live_readiness,
)
from smart_trade_backend.application.strategy.registry import (
    StrategySelectionError,
    select_strategy,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import CommandStatus, CommandType

SUPPORTED_COMMANDS = {
    CommandType.RETRAIN_MODEL,
    CommandType.SELECT_STRATEGY,
    CommandType.APPROVE_MODEL,
    CommandType.START_PAPER,
    CommandType.ENABLE_LIVE,
    CommandType.START_LIVE,
}


def create_command_request(
    session: Session,
    *,
    settings: Settings | None = None,
    command_type: CommandType,
    requested_by: str,
    payload: dict[str, Any],
) -> CommandRequestRecord:
    status = CommandStatus.REQUESTED
    result: dict[str, Any] = {}
    if command_type not in SUPPORTED_COMMANDS:
        status = CommandStatus.REJECTED
        result = {"reason": "Command type is not enabled."}
    elif command_type == CommandType.SELECT_STRATEGY and settings is not None:
        try:
            selected = select_strategy(
                session,
                settings,
                strategy_registry_id=int(payload["strategy_registry_id"]),
                parameters=payload.get("parameters") or {},
            )
        except (KeyError, TypeError, ValueError, StrategySelectionError) as exc:
            status = CommandStatus.FAILED
            result = {"reason": str(exc)}
        else:
            status = CommandStatus.COMPLETED
            result = {"selected_strategy_record_id": selected.id}
    elif command_type == CommandType.APPROVE_MODEL and settings is not None:
        try:
            approved = approve_model(
                session,
                settings,
                model_id=str(payload["model_id"]),
            )
        except (KeyError, TypeError, ValueError, ModelApprovalError) as exc:
            status = CommandStatus.FAILED
            result = {"reason": str(exc)}
        else:
            status = CommandStatus.COMPLETED
            result = {"model_id": approved.model_id, "status": approved.status}
    elif command_type == CommandType.START_PAPER and settings is not None:
        try:
            paper_run = run_paper_replay(
                session,
                settings,
                limit=int(payload.get("limit", 500)),
            )
        except (TypeError, ValueError, PaperRuntimeError) as exc:
            status = CommandStatus.FAILED
            result = {"reason": str(exc)}
        else:
            status = CommandStatus.COMPLETED
            result = {
                "processed_candles": paper_run.processed_candles,
                "decisions_created": paper_run.decisions_created,
                "orders_created": paper_run.orders_created,
                "fills_created": paper_run.fills_created,
                "equity_snapshots_created": paper_run.equity_snapshots_created,
                "open_position_id": paper_run.open_position_id,
            }
    elif command_type == CommandType.ENABLE_LIVE and settings is not None:
        try:
            review = enable_live_readiness(
                session,
                settings,
                requested_by=requested_by,
            )
        except LiveReadinessError as exc:
            status = CommandStatus.FAILED
            result = {"reason": str(exc)}
        else:
            status = CommandStatus.COMPLETED
            result = {
                "live_readiness_review_id": review.id,
                "status": review.status,
                "enabled_at": review.enabled_at.isoformat() if review.enabled_at else None,
            }
    elif command_type == CommandType.START_LIVE and settings is not None:
        try:
            live_result = execute_live_order(
                session,
                settings,
                side=str(payload["side"]).upper(),  # type: ignore[arg-type]
                idempotency_key=str(payload["idempotency_key"]),
                requested_by=requested_by,
                quote_amount_usd=Decimal(str(payload["quote_amount_usd"]))
                if payload.get("quote_amount_usd") is not None
                else None,
            )
        except (KeyError, TypeError, ValueError, LiveExecutionError) as exc:
            status = CommandStatus.FAILED
            result = {"reason": str(exc)}
        else:
            status = CommandStatus.COMPLETED
            result = {
                "order_id": live_result.order.id,
                "client_order_id": live_result.order.client_order_id,
                "status": live_result.order.status,
                "duplicate": live_result.duplicate,
            }

    record = CommandRequestRecord(
        command_type=command_type.value,
        status=status.value,
        requested_by=requested_by,
        payload=payload,
        requested_at=datetime.now(UTC),
        result=result,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
