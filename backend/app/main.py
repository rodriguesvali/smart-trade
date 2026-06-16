from __future__ import annotations

from fastapi import FastAPI

from app.adapters.api.routes import router
from app.adapters.persistence.sqlalchemy_repositories import SqlAlchemyStrategyRepository
from app.infrastructure.database import init_database
from app.strategy_catalog import seed_strategy_catalog
from app.infrastructure.database import SessionLocal


app = FastAPI(
    title="Smart Trade Backend",
    description="MVP backend for XGBoost strategy training, trained model inspection, and validation.",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_database()
    with SessionLocal() as session:
        seed_strategy_catalog(SqlAlchemyStrategyRepository(session))


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)
