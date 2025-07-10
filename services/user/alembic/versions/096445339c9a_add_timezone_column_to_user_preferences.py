"""add_timezone_column_to_user_preferences

Revision ID: 096445339c9a
Revises: add_normalized_email_column
Create Date: 2025-07-10 16:09:42.153216

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "096445339c9a"
down_revision = "add_normalized_email_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timezone column to user_preferences table
    op.add_column(
        "user_preferences",
        sa.Column(
            "timezone", sa.String(length=50), nullable=False, server_default="UTC"
        ),
    )


def downgrade() -> None:
    # Remove timezone column from user_preferences table
    op.drop_column("user_preferences", "timezone")
