from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Trade API"
    environment: str = "development"
    database_url: str = "mysql+pymysql://smart_trade:smart_trade@mysql:3306/smart_trade"
    run_migrations_on_startup: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SMART_TRADE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
