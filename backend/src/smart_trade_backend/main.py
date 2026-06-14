from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from smart_trade_backend.config import get_settings
from smart_trade_backend.db import check_database, create_db_engine
from smart_trade_backend.migrations import run_startup_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.run_migrations_on_startup:
        run_startup_migrations()
    app.state.settings = settings
    app.state.db_engine = create_db_engine(settings)
    yield
    app.state.db_engine.dispose()


app = FastAPI(title="Smart Trade API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/health/db")
def database_health() -> dict[str, Any]:
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        check_database(engine)
    finally:
        engine.dispose()

    return {
        "status": "ok",
        "database": "reachable",
    }
