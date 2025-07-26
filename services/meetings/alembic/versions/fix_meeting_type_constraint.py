"""Fix meeting_type constraint

Revision ID: fix_meeting_type_constraint
Revises: 5e45661a6eeb
Create Date: 2025-01-27 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_meeting_type_constraint"
down_revision = "5e45661a6eeb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a check constraint to ensure meeting_type only contains valid values
    op.create_check_constraint(
        "valid_meeting_type",
        "meeting_polls",
        "meeting_type IN ('in_person', 'virtual', 'tbd')",
    )


def downgrade() -> None:
    # Remove the check constraint
    op.drop_constraint("valid_meeting_type", "meeting_polls", type_="check")
