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
    with op.batch_alter_table("poll_participants") as batch_op:
        batch_op.add_column(
            sa.Column("response_token", sa.String(length=64), nullable=False),
        )
        batch_op.create_unique_constraint(
            "uq_poll_participants_response_token", ["response_token"]
        )


def downgrade():
    with op.batch_alter_table("poll_participants") as batch_op:
        batch_op.drop_constraint("uq_poll_participants_response_token", type_="unique")
        batch_op.drop_column("response_token")
