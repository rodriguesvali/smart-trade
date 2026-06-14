from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    EquitySnapshotRecord,
    FillRecord,
    LiveReadinessReviewRecord,
    ModelRegistryRecord,
    OperationalEventRecord,
    OrderRecord,
    PositionRecord,
    SelectedStrategyRecord,
    StrategyDecisionRecord,
    StrategyRegistryRecord,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import EventSeverity, ModelStatus, StrategyStatus


class LiveReadinessError(ValueError):
    pass


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    label: str
    passed: bool
    detail: str
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "label": self.label,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def live_readiness_status(session: Session, settings: Settings) -> dict[str, Any]:
    checks = evaluate_live_readiness(session, settings)
    latest_review = session.scalars(
        select(LiveReadinessReviewRecord)
        .order_by(desc(LiveReadinessReviewRecord.reviewed_at))
        .limit(1)
    ).first()
    failure_reasons = [check.detail for check in checks if not check.passed]
    return {
        "ready": not failure_reasons,
        "checks": [check.as_dict() for check in checks],
        "failure_reasons": failure_reasons,
        "latest_review": latest_review,
    }


def enable_live_readiness(
    session: Session,
    settings: Settings,
    *,
    requested_by: str,
) -> LiveReadinessReviewRecord:
    checks = evaluate_live_readiness(session, settings)
    failure_reasons = [check.detail for check in checks if not check.passed]
    now = datetime.now(UTC)
    review = LiveReadinessReviewRecord(
        status="READY" if not failure_reasons else "BLOCKED",
        requested_by=requested_by,
        reviewed_at=now,
        enabled_at=now if not failure_reasons else None,
        checks=[check.as_dict() for check in checks],
        evidence=readiness_evidence(session, settings),
        failure_reasons=failure_reasons,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    if failure_reasons:
        raise LiveReadinessError("; ".join(failure_reasons))
    return review


def evaluate_live_readiness(session: Session, settings: Settings) -> list[ReadinessCheck]:
    evidence = readiness_evidence(session, settings)
    return [
        _paper_days_check(evidence),
        _trade_count_check(evidence),
        _critical_events_check(evidence),
        _state_consistency_check(evidence),
        _traceability_check(evidence),
        _exchange_limits_check(evidence),
        _risk_thresholds_check(evidence),
    ]


def readiness_evidence(session: Session, settings: Settings) -> dict[str, Any]:
    paper_days = _paper_days(session, settings)
    trade_count = session.scalar(
        select(func.count())
        .select_from(FillRecord)
        .join(OrderRecord, FillRecord.order_id == OrderRecord.id)
        .where(
            OrderRecord.asset_symbol == settings.symbol,
            OrderRecord.side == "SELL",
            OrderRecord.raw_request["mode"].as_string() == "paper",
        )
    ) or 0
    critical_events = session.scalar(
        select(func.count())
        .select_from(OperationalEventRecord)
        .where(OperationalEventRecord.severity == EventSeverity.CRITICAL.value)
    ) or 0
    open_positions = session.scalar(
        select(func.count())
        .select_from(PositionRecord)
        .where(PositionRecord.asset_symbol == settings.symbol, PositionRecord.status == "OPEN")
    ) or 0
    traceability_failures = _traceability_failures(session, settings)
    selected_strategy = _selected_strategy(session)
    compatible_model_count = _compatible_model_count(session, settings, selected_strategy)
    latest_equity = session.scalars(
        select(EquitySnapshotRecord)
        .where(EquitySnapshotRecord.asset_symbol == settings.symbol)
        .order_by(desc(EquitySnapshotRecord.snapshot_at))
        .limit(1)
    ).first()
    max_drawdown = _paper_max_drawdown(session, settings)
    return {
        "paper_days": len(paper_days),
        "paper_day_dates": [item.isoformat() for item in paper_days],
        "simulated_trade_count": int(trade_count),
        "critical_event_count": int(critical_events),
        "open_position_count": int(open_positions),
        "traceability_failures": traceability_failures,
        "selected_strategy_id": selected_strategy.strategy_registry_id
        if selected_strategy is not None
        else None,
        "compatible_model_count": compatible_model_count,
        "latest_equity_usd": str(latest_equity.equity_usd) if latest_equity else None,
        "max_drawdown": max_drawdown,
        "exchange_limit_validation": {
            "symbol": settings.symbol,
            "timeframe": settings.timeframe,
            "market_type": "spot",
            "direction": "long_only",
            "validated": True,
            "source": (
                "MVP static spot-long-only constraints; "
                "private exchange validation deferred to B8."
            ),
        },
    }


def _paper_days(session: Session, settings: Settings) -> list[date]:
    rows = list(
        session.scalars(
            select(EquitySnapshotRecord.snapshot_at)
            .where(
                EquitySnapshotRecord.asset_symbol == settings.symbol,
                EquitySnapshotRecord.source == "paper",
            )
            .order_by(EquitySnapshotRecord.snapshot_at)
        )
    )
    dates = sorted({item.date() for item in rows})
    if not dates:
        return []
    longest: list[date] = []
    current = [dates[0]]
    for item in dates[1:]:
        if item == current[-1] + timedelta(days=1):
            current.append(item)
        elif item != current[-1]:
            if len(current) > len(longest):
                longest = current
            current = [item]
    if len(current) > len(longest):
        longest = current
    return longest


def _paper_days_check(evidence: dict[str, Any]) -> ReadinessCheck:
    days = int(evidence["paper_days"])
    return ReadinessCheck(
        check_id="paper_7_consecutive_days",
        label="7 consecutive paper days",
        passed=days >= 7,
        detail=f"Paper run has {days} consecutive day(s); 7 required.",
        evidence={"paper_days": days, "paper_day_dates": evidence["paper_day_dates"]},
    )


def _trade_count_check(evidence: dict[str, Any]) -> ReadinessCheck:
    trades = int(evidence["simulated_trade_count"])
    days = int(evidence["paper_days"])
    passed = trades >= 30 or days >= 7
    return ReadinessCheck(
        check_id="paper_trade_count_or_full_run",
        label="30 simulated trades or full 7-day run",
        passed=passed,
        detail=f"Paper evidence has {trades} simulated trade(s) and {days} consecutive day(s).",
        evidence={"simulated_trade_count": trades, "paper_days": days},
    )


def _critical_events_check(evidence: dict[str, Any]) -> ReadinessCheck:
    count = int(evidence["critical_event_count"])
    return ReadinessCheck(
        check_id="no_unresolved_critical_failures",
        label="No unresolved critical failures",
        passed=count == 0,
        detail=f"{count} critical operational event(s) are present.",
        evidence={"critical_event_count": count},
    )


def _state_consistency_check(evidence: dict[str, Any]) -> ReadinessCheck:
    open_positions = int(evidence["open_position_count"])
    return ReadinessCheck(
        check_id="consistent_position_order_state",
        label="Consistent position/order state",
        passed=open_positions <= 1,
        detail=f"{open_positions} open paper position(s) exist; at most one is allowed.",
        evidence={"open_position_count": open_positions},
    )


def _traceability_check(evidence: dict[str, Any]) -> ReadinessCheck:
    failures = list(evidence["traceability_failures"])
    detail = "Paper records include required strategy/model traceability."
    if evidence["selected_strategy_id"] is None:
        detail = "No selected strategy is available for live readiness."
    elif failures:
        detail = "Traceability failures: " + ", ".join(failures)
    return ReadinessCheck(
        check_id="complete_model_strategy_traceability",
        label="Complete model/strategy traceability",
        passed=not failures and evidence["selected_strategy_id"] is not None,
        detail=detail,
        evidence={
            "selected_strategy_id": evidence["selected_strategy_id"],
            "compatible_model_count": evidence["compatible_model_count"],
            "traceability_failures": failures,
        },
    )


def _exchange_limits_check(evidence: dict[str, Any]) -> ReadinessCheck:
    exchange_evidence = dict(evidence["exchange_limit_validation"])
    return ReadinessCheck(
        check_id="exchange_limit_validation",
        label="Exchange limit validation",
        passed=bool(exchange_evidence["validated"]),
        detail=exchange_evidence["source"],
        evidence=exchange_evidence,
    )


def _risk_thresholds_check(evidence: dict[str, Any]) -> ReadinessCheck:
    drawdown = Decimal(str(evidence["max_drawdown"]))
    threshold = Decimal("0.20")
    return ReadinessCheck(
        check_id="paper_risk_thresholds",
        label="Paper results within approved risk thresholds",
        passed=drawdown <= threshold and evidence["latest_equity_usd"] is not None,
        detail=f"Paper max drawdown is {drawdown}; threshold is {threshold}.",
        evidence={
            "max_drawdown": str(drawdown),
            "threshold": str(threshold),
            "latest_equity_usd": evidence["latest_equity_usd"],
        },
    )


def _traceability_failures(session: Session, settings: Settings) -> list[str]:
    failures: list[str] = []
    decisions = list(
        session.scalars(
            select(StrategyDecisionRecord).where(
                StrategyDecisionRecord.asset_symbol == settings.symbol
            )
        )
    )
    for decision in decisions:
        if not decision.strategy_id or not decision.strategy_version:
            failures.append(f"decision:{decision.id}:missing_strategy")
        if decision.action != "HOLD" and not decision.participating_models:
            failures.append(f"decision:{decision.id}:missing_model_refs")
        for model_ref in decision.participating_models:
            for key in ("model_id", "model_role", "strategy_id", "strategy_version"):
                if not model_ref.get(key):
                    failures.append(f"decision:{decision.id}:missing_{key}")
    positions = list(
        session.scalars(
            select(PositionRecord).where(PositionRecord.asset_symbol == settings.symbol)
        )
    )
    for position in positions:
        if not position.strategy_id or not position.strategy_version:
            failures.append(f"position:{position.id}:missing_strategy")
        if not position.model_refs:
            failures.append(f"position:{position.id}:missing_model_refs")
    return failures


def _selected_strategy(session: Session) -> SelectedStrategyRecord | None:
    return session.scalars(
        select(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == StrategyStatus.SELECTED.value)
        .order_by(desc(SelectedStrategyRecord.selected_at))
        .limit(1)
    ).first()


def _compatible_model_count(
    session: Session, settings: Settings, selected_strategy: SelectedStrategyRecord | None
) -> int:
    if selected_strategy is None:
        return 0
    strategy = session.get(StrategyRegistryRecord, selected_strategy.strategy_registry_id)
    if strategy is None:
        return 0
    roles = [str(role["role"]) for role in strategy.model_roles if "role" in role]
    if not roles:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(ModelRegistryRecord)
            .where(
                ModelRegistryRecord.status.in_(
                    [ModelStatus.APPROVED.value, ModelStatus.ACTIVE.value]
                ),
                ModelRegistryRecord.strategy_id == strategy.strategy_id,
                ModelRegistryRecord.strategy_version == strategy.version,
                ModelRegistryRecord.model_role.in_(roles),
                ModelRegistryRecord.asset_symbol == settings.symbol,
                ModelRegistryRecord.timeframe == settings.timeframe,
            )
        )
        or 0
    )


def _paper_max_drawdown(session: Session, settings: Settings) -> str:
    snapshots = list(
        session.scalars(
            select(EquitySnapshotRecord)
            .where(
                EquitySnapshotRecord.asset_symbol == settings.symbol,
                EquitySnapshotRecord.source == "paper",
            )
            .order_by(EquitySnapshotRecord.snapshot_at)
        )
    )
    if not snapshots:
        return "0"
    peak = snapshots[0].equity_usd
    max_drawdown = Decimal("0")
    for snapshot in snapshots:
        peak = max(peak, snapshot.equity_usd)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - snapshot.equity_usd) / peak)
    return str(max_drawdown)
