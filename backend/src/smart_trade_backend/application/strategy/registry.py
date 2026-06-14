from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from smart_trade_backend.adapters.persistence.models import (
    FeatureSchemaRecord,
    SelectedStrategyRecord,
    StrategyRegistryRecord,
)
from smart_trade_backend.config import Settings
from smart_trade_backend.domain.enums import MarketType, StrategyStatus, TradeDirection
from smart_trade_backend.domain.strategy.plugin import RuntimeStrategyContext, StrategyPlugin
from smart_trade_backend.strategies import discover_strategy_plugins


class StrategySelectionError(ValueError):
    pass


def register_available_strategies(session: Session) -> list[StrategyRegistryRecord]:
    records: list[StrategyRegistryRecord] = []
    for plugin in discover_strategy_plugins():
        records.append(register_strategy_plugin(session, plugin))
    return records


def register_strategy_plugin(
    session: Session, plugin: StrategyPlugin
) -> StrategyRegistryRecord:
    config_errors = plugin.validate_config(plugin.metadata.default_parameters)
    if config_errors:
        raise ValueError(
            f"Strategy {plugin.metadata.strategy_id} default config is invalid: "
            + "; ".join(config_errors)
        )

    existing = session.scalar(
        select(StrategyRegistryRecord).where(
            StrategyRegistryRecord.strategy_id == plugin.metadata.strategy_id,
            StrategyRegistryRecord.version == plugin.metadata.version,
        )
    )
    values = {
        "name": plugin.metadata.name,
        "description": plugin.metadata.description,
        "status": StrategyStatus.REGISTERED.value,
        "supported_market": plugin.metadata.supported_market.value,
        "supported_direction": plugin.metadata.supported_direction.value,
        "timeframes": list(plugin.metadata.timeframes),
        "parameter_schema": plugin.metadata.parameter_schema,
        "default_parameters": plugin.metadata.default_parameters,
        "required_features": list(plugin.required_features(plugin.metadata.default_parameters)),
        "model_roles": [
            role.as_dict()
            for role in plugin.required_model_roles(plugin.metadata.default_parameters)
        ],
    }
    if existing is None:
        record = StrategyRegistryRecord(
            strategy_id=plugin.metadata.strategy_id,
            version=plugin.metadata.version,
            **values,
        )
        session.add(record)
    else:
        record = existing
        for key, value in values.items():
            setattr(record, key, value)
    session.commit()
    session.refresh(record)
    return record


def select_strategy(
    session: Session,
    settings: Settings,
    *,
    strategy_registry_id: int,
    parameters: dict[str, Any] | None = None,
) -> SelectedStrategyRecord:
    record = session.get(StrategyRegistryRecord, strategy_registry_id)
    if record is None:
        raise StrategySelectionError("Strategy does not exist.")

    plugin = _plugin_for_record(record)
    selected_parameters = {**record.default_parameters, **(parameters or {})}
    config_errors = plugin.validate_config(selected_parameters)
    if config_errors:
        raise StrategySelectionError("; ".join(config_errors))

    context = _runtime_context(session, settings)
    compatibility = plugin.compatibility_check(context)
    if not compatibility.compatible:
        raise StrategySelectionError("; ".join(compatibility.reasons))

    session.execute(
        update(SelectedStrategyRecord)
        .where(SelectedStrategyRecord.status == StrategyStatus.SELECTED.value)
        .values(status=StrategyStatus.INACTIVE.value, deselected_at=datetime.now(UTC))
    )
    selected = SelectedStrategyRecord(
        strategy_registry_id=record.id,
        status=StrategyStatus.SELECTED.value,
        parameters=selected_parameters,
        selected_at=datetime.now(UTC),
    )
    session.add(selected)
    session.commit()
    session.refresh(selected)
    return selected


def strategy_compatibility(
    session: Session, settings: Settings, record: StrategyRegistryRecord
) -> dict[str, Any]:
    plugin = _plugin_for_record(record)
    compatibility = plugin.compatibility_check(_runtime_context(session, settings))
    config_errors = plugin.validate_config(record.default_parameters)
    return {
        "compatible": compatibility.compatible and not config_errors,
        "reasons": list(compatibility.reasons) + list(config_errors),
        "risk_rules": [rule.as_dict() for rule in plugin.risk_rules(record.default_parameters)],
    }


def _plugin_for_record(record: StrategyRegistryRecord) -> StrategyPlugin:
    for plugin in discover_strategy_plugins():
        if (
            plugin.metadata.strategy_id == record.strategy_id
            and plugin.metadata.version == record.version
        ):
            return plugin
    raise StrategySelectionError("Strategy plugin is not deployed in code.")


def _runtime_context(session: Session, settings: Settings) -> RuntimeStrategyContext:
    schemas = list(session.scalars(select(FeatureSchemaRecord)))
    available_features = tuple(
        sorted({feature for schema in schemas for feature in schema.features})
    )
    available_schema_ids = tuple(sorted(schema.schema_id for schema in schemas))
    return RuntimeStrategyContext(
        exchange=settings.exchange,
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        market_type=MarketType.SPOT,
        direction=TradeDirection.LONG_ONLY,
        available_feature_schema_ids=available_schema_ids,
        available_features=available_features,
    )
