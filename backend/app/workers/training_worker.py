from __future__ import annotations

import logging
import time

from app.adapters.persistence.sqlalchemy_repositories import SqlAlchemyStrategyRepository
from app.infrastructure.config import get_settings
from app.infrastructure.container import build_training_use_cases
from app.infrastructure.database import SessionLocal, init_database
from app.strategy_catalog import seed_strategy_catalog


logger = logging.getLogger("smart_trade.training_worker")


def run_once(worker_id: str | None = None) -> bool:
    settings = get_settings()
    active_worker_id = worker_id or settings.worker_id
    with SessionLocal() as session:
        use_cases = build_training_use_cases(session)
        try:
            run = use_cases.execute_next_training(active_worker_id)
        except Exception:
            session.rollback()
            logger.exception("Training worker failed while processing a run")
            return True
        if run is None:
            return False
        logger.info("Processed training run %s with status %s", run.id, run.status.value)
        return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    init_database()
    with SessionLocal() as session:
        seed_strategy_catalog(SqlAlchemyStrategyRepository(session))

    logger.info("Training worker %s started", settings.worker_id)
    while True:
        processed = run_once(settings.worker_id)
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
