from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import CommandRequestRecord
from smart_trade_backend.application.model_training.service import (
    ModelApprovalError,
    approve_model,
)
from smart_trade_backend.application.paper.runtime import PaperRuntimeError, run_paper_replay
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
