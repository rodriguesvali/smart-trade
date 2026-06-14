"""B3 market data and feature schema.

Revision ID: 20260614_0002
Revises: 20260614_0001
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260614_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("open_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(28, 12), nullable=False),
        sa.Column("high", sa.Numeric(28, 12), nullable=False),
        sa.Column("low", sa.Numeric(28, 12), nullable=False),
        sa.Column("close", sa.Numeric(28, 12), nullable=False),
        sa.Column("volume", sa.Numeric(28, 12), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exchange",
            "symbol",
            "timeframe",
            "open_time_ms",
            name="uq_candles_market_time",
        ),
    )
    op.create_index(
        "ix_candles_market_time",
        "candles",
        ["exchange", "symbol", "timeframe", "open_time_ms"],
    )
    op.create_index("ix_candles_opened_at", "candles", ["opened_at"])

    op.create_table(
        "feature_schemas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("schema_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id"),
    )
    op.create_index("ix_feature_schemas_identity", "feature_schemas", ["name", "version"])

    op.create_table(
        "candle_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("feature_schema_id", sa.String(length=128), nullable=False),
        sa.Column("open_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("candle_opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exchange",
            "symbol",
            "timeframe",
            "feature_schema_id",
            "open_time_ms",
            name="uq_candle_features_market_schema_time",
        ),
    )
    op.create_index(
        "ix_candle_features_market_schema_time",
        "candle_features",
        ["exchange", "symbol", "timeframe", "feature_schema_id", "open_time_ms"],
    )

    op.create_table(
        "data_ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("since_ms", sa.BigInteger(), nullable=True),
        sa.Column("until_ms", sa.BigInteger(), nullable=True),
        sa.Column("requested_limit", sa.Integer(), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("feature_rows_upserted", sa.Integer(), nullable=False),
        sa.Column("first_open_time_ms", sa.BigInteger(), nullable=True),
        sa.Column("last_open_time_ms", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_ingestion_runs_market_started",
        "data_ingestion_runs",
        ["exchange", "symbol", "timeframe", "started_at"],
    )
    op.create_index("ix_data_ingestion_runs_status", "data_ingestion_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_data_ingestion_runs_status", table_name="data_ingestion_runs")
    op.drop_index("ix_data_ingestion_runs_market_started", table_name="data_ingestion_runs")
    op.drop_table("data_ingestion_runs")
    op.drop_index("ix_candle_features_market_schema_time", table_name="candle_features")
    op.drop_table("candle_features")
    op.drop_index("ix_feature_schemas_identity", table_name="feature_schemas")
    op.drop_table("feature_schemas")
    op.drop_index("ix_candles_opened_at", table_name="candles")
    op.drop_index("ix_candles_market_time", table_name="candles")
    op.drop_table("candles")
