from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Trade API"
    environment: str = "development"
    database_url: str = "mysql+pymysql://smart_trade:smart_trade@mysql:3306/smart_trade"
    run_migrations_on_startup: bool = True
    register_strategies_on_startup: bool = True
    exchange: str = "bybit"
    symbol: str = "BTC/USDT"
    timeframe: str = "1m"
    initial_capital_usd: float = 1000.0
    mode: str = "paper"
    historical_ingestion_limit: int = 1000
    historical_ingestion_page_size: int = 200
    candle_retention_days: int = 120
    feature_retention_days: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SMART_TRADE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
