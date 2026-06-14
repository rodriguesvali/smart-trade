from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import CommandRequestRecord
from smart_trade_backend.domain.enums import CommandStatus, CommandType

SUPPORTED_B1_COMMANDS = {
    CommandType.RETRAIN_MODEL,
    CommandType.SELECT_STRATEGY,
    CommandType.APPROVE_MODEL,
}


def create_command_request(
    session: Session,
    *,
    command_type: CommandType,
    requested_by: str,
    payload: dict[str, Any],
) -> CommandRequestRecord:
    status = CommandStatus.REQUESTED
    result: dict[str, Any] = {}
    if command_type not in SUPPORTED_B1_COMMANDS:
        status = CommandStatus.REJECTED
        result = {"reason": "Command type is not enabled in B1."}

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

