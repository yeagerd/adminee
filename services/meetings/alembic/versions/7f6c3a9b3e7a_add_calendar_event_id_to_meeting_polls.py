"""add_calendar_event_id_to_meeting_polls

Revision ID: 7f6c3a9b3e7a
Revises: 516af99cbe18
Create Date: 2025-08-12 20:55:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7f6c3a9b3e7a"
down_revision = "516af99cbe18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add calendar_event_id column to meeting_polls table
    op.add_column(
        "meeting_polls",
        sa.Column("calendar_event_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    # Remove calendar_event_id column from meeting_polls table
    op.drop_column("meeting_polls", "calendar_event_id")
