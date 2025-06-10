"""Add deleted_at field to users table

Revision ID: eae3ad795a11
Revises: 1414759bab80
Create Date: 2025-06-10 10:14:39.199263

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eae3ad795a11"
down_revision = "1414759bab80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deleted_at column to users table
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove deleted_at column from users table
    op.drop_column("users", "deleted_at")
