"""add_user_drafts_table

Revision ID: a46de6cb2186
Revises: adc3b74054c1
Create Date: 2025-07-14 21:56:36.517801

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a46de6cb2186"
down_revision: Union[str, None] = "adc3b74054c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False
        ),
        sa.Column("type", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("draft_metadata", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_drafts_user_id"), "user_drafts", ["user_id"], unique=False
    )
    op.create_index(op.f("ix_user_drafts_type"), "user_drafts", ["type"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_user_drafts_type"), table_name="user_drafts")
    op.drop_index(op.f("ix_user_drafts_user_id"), table_name="user_drafts")
    op.drop_table("user_drafts")
    # ### end Alembic commands ###
