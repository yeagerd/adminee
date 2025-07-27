"""Fix meeting_type constraint

Revision ID: fix_meeting_type_constraint
Revises: 5e45661a6eeb
Create Date: 2025-01-27 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "fix_meeting_type_constraint"
down_revision = "5e45661a6eeb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("meeting_polls", schema=None) as batch_op:
        # Add a check constraint to ensure meeting_type only contains valid values
        batch_op.create_check_constraint(
            "valid_meeting_type",
            "meeting_type IN ('in_person', 'virtual', 'tbd')",
        )


def downgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("meeting_polls", schema=None) as batch_op:
        # Remove the check constraint
        batch_op.drop_constraint("valid_meeting_type", type_="check")
