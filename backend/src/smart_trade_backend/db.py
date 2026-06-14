from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from smart_trade_backend.config import Settings


class Base(DeclarativeBase):
    pass


def create_db_engine(settings: Settings) -> Engine:
    if settings.database_url == "sqlite+pysqlite:///:memory:":
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session]:
    with session_factory() as session:
        yield session


def check_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
