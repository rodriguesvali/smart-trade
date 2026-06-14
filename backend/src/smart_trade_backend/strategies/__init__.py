from smart_trade_backend.domain.strategy.plugin import StrategyPlugin
from smart_trade_backend.strategies.default_rsi_xgboost import DefaultRsiXgboostStrategy


def discover_strategy_plugins() -> tuple[StrategyPlugin, ...]:
    """Return code-deployed strategy plugins available to the backend."""

    return (DefaultRsiXgboostStrategy(),)


__all__ = ["discover_strategy_plugins"]
