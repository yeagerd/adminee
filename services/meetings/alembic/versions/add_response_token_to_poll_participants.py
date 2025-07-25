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
    import uuid

    from sqlalchemy.sql import column, table

    # 1. Add as nullable
    with op.batch_alter_table("poll_participants") as batch_op:
        batch_op.add_column(
            sa.Column("response_token", sa.String(length=64), nullable=True),
        )

    # 2. Populate with unique values for existing rows
    poll_participants = table(
        "poll_participants",
        column("id", sa.String),
        column("response_token", sa.String(64)),
    )
    conn = op.get_bind()
    results = conn.execute(
        sa.text("SELECT id FROM poll_participants WHERE response_token IS NULL")
    ).fetchall()
    for row in results:
        conn.execute(
            poll_participants.update()
            .where(poll_participants.c.id == row[0])
            .values(response_token=str(uuid.uuid4()))
        )

    # 3. Alter to NOT NULL
    with op.batch_alter_table("poll_participants") as batch_op:
        batch_op.alter_column("response_token", nullable=False)
        batch_op.create_unique_constraint(
            "uq_poll_participants_response_token", ["response_token"]
        )


def downgrade():
    with op.batch_alter_table("poll_participants") as batch_op:
        batch_op.drop_constraint("uq_poll_participants_response_token", type_="unique")
        batch_op.drop_column("response_token")
