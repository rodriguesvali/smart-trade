from enum import StrEnum


class MarketType(StrEnum):
    SPOT = "spot"


class TradeDirection(StrEnum):
    LONG_ONLY = "long_only"


class StrategyStatus(StrEnum):
    REGISTERED = "REGISTERED"
    SELECTED = "SELECTED"
    INACTIVE = "INACTIVE"
    REJECTED = "REJECTED"


class ModelStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    BACKTESTED = "BACKTESTED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class OperationMode(StrEnum):
    TRAINING = "training"
    PAPER = "paper"
    LIVE = "live"


class OperationState(StrEnum):
    NOT_READY = "NOT_READY"
    IDLE = "IDLE"
    TRAINING = "TRAINING"
    PAPER_RUNNING = "PAPER_RUNNING"
    LIVE_RUNNING = "LIVE_RUNNING"
    BLOCKED = "BLOCKED"


class CommandType(StrEnum):
    RETRAIN_MODEL = "RETRAIN_MODEL"
    APPROVE_MODEL = "APPROVE_MODEL"
    SELECT_STRATEGY = "SELECT_STRATEGY"
    START_PAPER = "START_PAPER"
    ENABLE_LIVE = "ENABLE_LIVE"
    START_LIVE = "START_LIVE"
    STOP_OPERATION = "STOP_OPERATION"


class CommandStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DecisionAction(StrEnum):
    HOLD = "HOLD"
    ENTER_LONG = "ENTER_LONG"
    MOVE_STOP = "MOVE_STOP"
    EXIT_POSITION = "EXIT_POSITION"


class PositionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class OrderStatus(StrEnum):
    REQUESTED = "REQUESTED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class EventSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
