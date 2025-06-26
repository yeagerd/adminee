"""Add normalized_email column to users table

Revision ID: add_normalized_email_column
Revises: c63ab04c63a9
Create Date: 2025-01-27 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_normalized_email_column"
down_revision = "c63ab04c63a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add normalized_email column
    op.add_column(
        "users", sa.Column("normalized_email", sa.String(length=255), nullable=True)
    )

    # Create index on normalized_email for performance
    op.create_index(
        op.f("ix_users_normalized_email"), "users", ["normalized_email"], unique=False
    )

    # Create unique index on normalized_email excluding soft-deleted users
    # Note: This is a partial unique index that only applies when deleted_at IS NULL
    op.create_index(
        "ix_users_normalized_email_unique_active",
        "users",
        ["normalized_email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    # Drop the unique index first
    op.drop_index("ix_users_normalized_email_unique_active", table_name="users")

    # Drop the regular index
    op.drop_index(op.f("ix_users_normalized_email"), table_name="users")

    # Drop the column
    op.drop_column("users", "normalized_email")
