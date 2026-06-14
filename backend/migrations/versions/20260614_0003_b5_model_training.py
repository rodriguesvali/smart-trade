"""B5 model training, validation, and backtest evidence.

Revision ID: 20260614_0003
Revises: 20260614_0002
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260614_0003"
down_revision = "20260614_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_training_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("model_role", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("feature_schema_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("holdout_rows", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id"),
    )
    op.create_index("ix_model_training_runs_status", "model_training_runs", ["status"])
    op.create_index(
        "ix_model_training_runs_model_role",
        "model_training_runs",
        ["strategy_id", "strategy_version", "model_role"],
    )

    op.create_table(
        "walk_forward_windows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("train_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("precision_class_1", sa.Numeric(10, 8), nullable=False),
        sa.Column("predicted_positive_count", sa.Integer(), nullable=False),
        sa.Column("actual_positive_count", sa.Integer(), nullable=False),
        sa.Column("acceptable", sa.Boolean(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "window_index", name="uq_walk_forward_model_window"),
    )
    op.create_index("ix_walk_forward_windows_model_id", "walk_forward_windows", ["model_id"])

    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("trade_index", sa.Integer(), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("exit_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 12), nullable=False),
        sa.Column("pnl", sa.Numeric(28, 12), nullable=False),
        sa.Column("pnl_pct", sa.Numeric(18, 10), nullable=False),
        sa.Column("exit_reason", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "trade_index", name="uq_backtest_trades_model_index"),
    )
    op.create_index("ix_backtest_trades_model_id", "backtest_trades", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_trades_model_id", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_index("ix_walk_forward_windows_model_id", table_name="walk_forward_windows")
    op.drop_table("walk_forward_windows")
    op.drop_index("ix_model_training_runs_model_role", table_name="model_training_runs")
    op.drop_index("ix_model_training_runs_status", table_name="model_training_runs")
    op.drop_table("model_training_runs")
