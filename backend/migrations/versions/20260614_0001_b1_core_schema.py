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


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

