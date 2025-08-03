"""
add_timezone_mode_and_manual_timezone_to_user_preferences

Revision ID: add_timezone_mode_manual
Revises: 096445339c9a
Create Date: 2024-07-10 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_timezone_mode_manual"
down_revision = "096445339c9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "timezone_mode", sa.String(length=10), nullable=False, server_default="auto"
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "manual_timezone", sa.String(length=50), nullable=False, server_default=""
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "manual_timezone")
    op.drop_column("user_preferences", "timezone_mode")
