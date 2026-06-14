"""B7 live readiness review evidence.

Revision ID: 20260614_0004
Revises: 20260614_0003
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260614_0004"
down_revision = "20260614_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "live_readiness_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("failure_reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_live_readiness_reviews_status",
        "live_readiness_reviews",
        ["status"],
    )
    op.create_index(
        "ix_live_readiness_reviews_reviewed_at",
        "live_readiness_reviews",
        ["reviewed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_live_readiness_reviews_reviewed_at", table_name="live_readiness_reviews")
    op.drop_index("ix_live_readiness_reviews_status", table_name="live_readiness_reviews")
    op.drop_table("live_readiness_reviews")
