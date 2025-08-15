"""add_recipient_name_to_one_time_links

Revision ID: add_recipient_name_column
Revises: 8c4a1b9d2f31
Create Date: 2025-01-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_recipient_name_column"
down_revision = "8c4a1b9d2f31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add recipient_name column to one_time_links table
    op.add_column(
        "one_time_links",
        sa.Column("recipient_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    # Remove recipient_name column from one_time_links table
    op.drop_column("one_time_links", "recipient_name")
