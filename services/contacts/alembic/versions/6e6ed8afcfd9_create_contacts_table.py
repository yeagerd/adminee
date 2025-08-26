"""create_contacts_table

Revision ID: 6e6ed8afcfd9
Revises:
Create Date: 2025-08-25 13:15:53.304168

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e6ed8afcfd9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create contacts table
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("email_address", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("given_name", sa.String(), nullable=True),
        sa.Column("family_name", sa.String(), nullable=True),
        sa.Column("event_counts", sa.JSON(), nullable=True),
        sa.Column("total_event_count", sa.Integer(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("relevance_factors", sa.JSON(), nullable=True),
        sa.Column("source_services", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column("phone_numbers", sa.JSON(), nullable=True),
        sa.Column("addresses", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for common query patterns
    op.create_index("idx_contacts_user_id", "contacts", ["user_id"])
    op.create_index("idx_contacts_email", "contacts", ["email_address"])
    op.create_index("idx_contacts_relevance", "contacts", ["relevance_score"])
    op.create_index("idx_contacts_last_seen", "contacts", ["last_seen"])

    # Create unique constraint for user_id + email_address combination
    op.create_unique_constraint(
        "idx_contacts_user_email", "contacts", ["user_id", "email_address"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_contacts_user_email", table_name="contacts")
    op.drop_index("idx_contacts_last_seen", table_name="contacts")
    op.drop_index("idx_contacts_relevance", table_name="contacts")
    op.drop_index("idx_contacts_email", table_name="contacts")
    op.drop_index("idx_contacts_user_id", table_name="contacts")

    # Drop table
    op.drop_table("contacts")
