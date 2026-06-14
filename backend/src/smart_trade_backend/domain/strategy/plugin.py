from dataclasses import dataclass, field
from typing import Any, Protocol

from smart_trade_backend.domain.enums import MarketType, TradeDirection


@dataclass(frozen=True)
class RuntimeStrategyContext:
    exchange: str
    symbol: str
    timeframe: str
    market_type: MarketType
    direction: TradeDirection
    available_feature_schema_ids: tuple[str, ...] = ()
    available_features: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyModelRole:
    role: str
    purpose: str
    model_type: str = "xgboost"
    output_contract: str = "binary"
    required_statuses: tuple[str, ...] = ("APPROVED", "ACTIVE")

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "purpose": self.purpose,
            "model_type": self.model_type,
            "output_contract": self.output_contract,
            "required_statuses": list(self.required_statuses),
        }


@dataclass(frozen=True)
class StrategyRiskRule:
    rule_id: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class CompatibilityResult:
    compatible: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyPluginMetadata:
    strategy_id: str
    version: str
    name: str
    description: str
    supported_market: MarketType
    supported_direction: TradeDirection
    timeframes: tuple[str, ...]
    parameter_schema: dict[str, Any]
    default_parameters: dict[str, Any]


class StrategyPlugin(Protocol):
    metadata: StrategyPluginMetadata

    def required_features(self, config: dict[str, Any]) -> tuple[str, ...]:
        """Return feature names required by this strategy configuration."""

    def required_model_roles(self, config: dict[str, Any]) -> tuple[StrategyModelRole, ...]:
        """Return model roles required before operation may start."""

    def validate_config(self, config: dict[str, Any]) -> tuple[str, ...]:
        """Return validation errors. Empty tuple means valid."""

    def risk_rules(self, config: dict[str, Any]) -> tuple[StrategyRiskRule, ...]:
        """Return explicit risk rules declared by the strategy."""

    def compatibility_check(self, runtime_context: RuntimeStrategyContext) -> CompatibilityResult:
        """Validate runtime compatibility without selecting or starting operation."""
