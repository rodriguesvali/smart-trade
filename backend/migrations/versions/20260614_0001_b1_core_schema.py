"""B1 core domain schema.

Revision ID: 20260614_0001
Revises:
Create Date: 2026-06-14
"""

from alembic import op

from smart_trade_backend.adapters.persistence import models  # noqa: F401
from smart_trade_backend.db import Base

revision = "20260614_0001"
down_revision = None
branch_labels = None
depends_on = None

B1_TABLES = (
    "asset_configurations",
    "strategy_registry",
    "selected_strategies",
    "model_registry",
    "strategy_decisions",
    "positions",
    "orders",
    "fills",
    "equity_snapshots",
    "command_requests",
    "operational_events",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in B1_TABLES:
        Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(B1_TABLES):
        Base.metadata.tables[table_name].drop(bind=bind, checkfirst=True)
