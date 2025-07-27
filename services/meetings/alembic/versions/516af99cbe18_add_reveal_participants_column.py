"""add_reveal_participants_column

Revision ID: 516af99cbe18
Revises: fix_meeting_type_constraint
Create Date: 2025-07-27 11:09:10.164046

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "516af99cbe18"
down_revision = "fix_meeting_type_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reveal_participants column to meeting_polls table
    op.add_column(
        "meeting_polls",
        sa.Column(
            "reveal_participants", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    # Remove reveal_participants column from meeting_polls table
    op.drop_column("meeting_polls", "reveal_participants")
