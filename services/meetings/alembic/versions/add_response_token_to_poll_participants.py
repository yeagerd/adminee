"""add response_token to poll_participants

Revision ID: add_response_token_to_poll_participants
Revises: c52ef2783d8a
Create Date: 2024-07-24 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_response_token_to_poll_participants"
down_revision = "c52ef2783d8a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "poll_participants",
        sa.Column("response_token", sa.String(length=64), nullable=False),
    )
    op.create_unique_constraint(
        "uq_poll_participants_response_token", "poll_participants", ["response_token"]
    )


def downgrade():
    op.drop_constraint(
        "uq_poll_participants_response_token", "poll_participants", type_="unique"
    )
    op.drop_column("poll_participants", "response_token")
