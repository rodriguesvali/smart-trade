from typing import Any

from pydantic import BaseModel, Field, ValidationError

from smart_trade_backend.domain.enums import MarketType, TradeDirection
from smart_trade_backend.domain.strategy.plugin import (
    CompatibilityResult,
    RuntimeStrategyContext,
    StrategyModelRole,
    StrategyPluginMetadata,
    StrategyRiskRule,
)


class DefaultRsiXgboostParameters(BaseModel):
    rsi_period: int = Field(default=14, ge=2, le=100)
    oversold_threshold: float = Field(default=30.0, gt=0, lt=50)
    stop_loss_pct: float = Field(default=0.015, gt=0, le=0.20)
    take_profit_pct: float = Field(default=0.03, gt=0, le=0.50)
    break_even_trigger_pct: float = Field(default=0.012, gt=0, le=0.50)
    trailing_stop_pct: float = Field(default=0.01, gt=0, le=0.20)
    min_model_probability: float = Field(default=0.5, ge=0.5, le=1.0)


class DefaultRsiXgboostStrategy:
    metadata = StrategyPluginMetadata(
        strategy_id="default_rsi_xgboost_long",
        version="1.0.0",
        name="RSI/IFR Oversold + XGBoost Confirmation",
        description=(
            "Default MVP spot long-only strategy. Entry requires RSI/IFR oversold context "
            "and a binary XGBoost confirmation model role."
        ),
        supported_market=MarketType.SPOT,
        supported_direction=TradeDirection.LONG_ONLY,
        timeframes=("1m",),
        parameter_schema=DefaultRsiXgboostParameters.model_json_schema(),
        default_parameters=DefaultRsiXgboostParameters().model_dump(),
    )

    def required_features(self, config: dict[str, Any]) -> tuple[str, ...]:
        self._validated(config)
        return (
            "rsi_14",
            "bb_upper_20_2",
            "bb_middle_20",
            "bb_lower_20_2",
            "return_1",
            "log_return_1",
            "volume_change_1",
            "atr_14",
            "body_pct",
        )

    def required_model_roles(self, config: dict[str, Any]) -> tuple[StrategyModelRole, ...]:
        self._validated(config)
        return (
            StrategyModelRole(
                role="entry_confirmation",
                purpose="Confirm long entry/continuation after RSI/IFR oversold setup.",
            ),
        )

    def validate_config(self, config: dict[str, Any]) -> tuple[str, ...]:
        try:
            params = self._validated(config)
        except ValidationError as exc:
            return tuple(error["msg"] for error in exc.errors())

        errors: list[str] = []
        if params.take_profit_pct <= params.stop_loss_pct:
            errors.append("take_profit_pct must be greater than stop_loss_pct.")
        if params.trailing_stop_pct >= params.take_profit_pct:
            errors.append("trailing_stop_pct must be lower than take_profit_pct.")
        return tuple(errors)

    def risk_rules(self, config: dict[str, Any]) -> tuple[StrategyRiskRule, ...]:
        params = self._validated(config)
        return (
            StrategyRiskRule(
                rule_id="spot_long_only",
                description="Strategy may only open long spot positions.",
            ),
            StrategyRiskRule(
                rule_id="one_position_only",
                description="Strategy must not increase or scale an existing open position.",
            ),
            StrategyRiskRule(
                rule_id="initial_stop_loss",
                description="Every entry requires an initial stop loss.",
                parameters={"stop_loss_pct": params.stop_loss_pct},
            ),
            StrategyRiskRule(
                rule_id="take_profit_or_protected_exit",
                description="Every entry requires take-profit/protected-exit behavior.",
                parameters={
                    "take_profit_pct": params.take_profit_pct,
                    "break_even_trigger_pct": params.break_even_trigger_pct,
                    "trailing_stop_pct": params.trailing_stop_pct,
                },
            ),
        )

    def compatibility_check(self, runtime_context: RuntimeStrategyContext) -> CompatibilityResult:
        reasons: list[str] = []
        if runtime_context.market_type != self.metadata.supported_market:
            reasons.append("Strategy supports spot market only.")
        if runtime_context.direction != self.metadata.supported_direction:
            reasons.append("Strategy supports long-only direction only.")
        if runtime_context.timeframe not in self.metadata.timeframes:
            reasons.append("Strategy supports M1/1m timeframe only.")

        required_features = set(self.required_features(self.metadata.default_parameters))
        missing = sorted(required_features.difference(runtime_context.available_features))
        if missing:
            reasons.append(f"Missing required features: {', '.join(missing)}.")

        return CompatibilityResult(compatible=not reasons, reasons=tuple(reasons))

    def _validated(self, config: dict[str, Any]) -> DefaultRsiXgboostParameters:
        merged = {**self.metadata.default_parameters, **config}
        return DefaultRsiXgboostParameters.model_validate(merged)
