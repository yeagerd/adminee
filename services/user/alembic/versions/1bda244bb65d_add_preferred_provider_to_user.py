"""add_preferred_provider_to_user

Revision ID: 1bda244bb65d
Revises: e6d4a2261255
Create Date: 2025-07-14 13:17:37.510375

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1bda244bb65d"
down_revision = "e6d4a2261255"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preferred_provider column to users table
    op.add_column(
        "users", sa.Column("preferred_provider", sa.String(50), nullable=True)
    )


def downgrade() -> None:
    # Remove preferred_provider column from users table
    op.drop_column("users", "preferred_provider")
