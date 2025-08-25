"""Add office integration fields to contacts table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add office integration fields
    op.add_column("contacts", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("contacts", sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contacts", sa.Column("phone_numbers", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("contacts", sa.Column("addresses", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create index for provider field
    op.create_index("idx_contacts_provider", "contacts", ["provider"])


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_contacts_provider", table_name="contacts")
    
    # Drop columns
    op.drop_column("contacts", "addresses")
    op.drop_column("contacts", "phone_numbers")
    op.drop_column("contacts", "last_synced")
    op.drop_column("contacts", "provider")
