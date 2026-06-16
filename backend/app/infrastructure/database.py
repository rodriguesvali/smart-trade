from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.infrastructure.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    if "///" in settings.database_url:
        db_path = settings.database_url.split("///", 1)[1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database() -> None:
    import app.adapters.persistence.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_compatibility_migrations()


def _apply_compatibility_migrations() -> None:
    inspector = inspect(engine)
    if "training_runs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("training_runs")}
    missing_columns = {
        "auto_validate": "BOOLEAN NOT NULL DEFAULT 0",
        "progress_phase": "VARCHAR(80)",
        "progress_pct": "FLOAT",
        "progress_message": "TEXT",
        "worker_id": "VARCHAR(120)",
        "locked_at": "DATETIME",
        "heartbeat_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_sql in missing_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE training_runs ADD COLUMN {column_name} {column_sql}"))


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
