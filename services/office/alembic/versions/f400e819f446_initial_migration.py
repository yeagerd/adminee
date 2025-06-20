"""Initial migration

Revision ID: f400e819f446
Revises:
Create Date: 2025-06-08 15:31:35.968274

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f400e819f446"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "api_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_api_calls_created_at"), "api_calls", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_api_calls_user_id"), "api_calls", ["user_id"], unique=False
    )
    op.create_table(
        "cache_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_accessed", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cache_entries_cache_key"), "cache_entries", ["cache_key"], unique=True
    )
    op.create_index(
        op.f("ix_cache_entries_expires_at"),
        "cache_entries",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cache_entries_user_id"), "cache_entries", ["user_id"], unique=False
    )
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("bucket_type", sa.String(length=50), nullable=False),
        sa.Column("current_count", sa.Integer(), nullable=True),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("last_reset", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rate_limit_buckets_user_id"),
        "rate_limit_buckets",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rate_limit_buckets_window_start"),
        "rate_limit_buckets",
        ["window_start"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_rate_limit_buckets_window_start"), table_name="rate_limit_buckets"
    )
    op.drop_index(
        op.f("ix_rate_limit_buckets_user_id"), table_name="rate_limit_buckets"
    )
    op.drop_table("rate_limit_buckets")
    op.drop_index(op.f("ix_cache_entries_user_id"), table_name="cache_entries")
    op.drop_index(op.f("ix_cache_entries_expires_at"), table_name="cache_entries")
    op.drop_index(op.f("ix_cache_entries_cache_key"), table_name="cache_entries")
    op.drop_table("cache_entries")
    op.drop_index(op.f("ix_api_calls_user_id"), table_name="api_calls")
    op.drop_index(op.f("ix_api_calls_created_at"), table_name="api_calls")
    op.drop_table("api_calls")
    # ### end Alembic commands ###
