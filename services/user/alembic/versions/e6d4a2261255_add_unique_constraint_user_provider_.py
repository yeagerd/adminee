"""add_unique_constraint_user_provider_integrations

Revision ID: e6d4a2261255
Revises: 096445339c9a
Create Date: 2025-07-13 00:08:25.975227

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e6d4a2261255"
down_revision = "096445339c9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("integrations") as batch_op:
        # First, handle any existing duplicate records by keeping only the most recent one
        # This is a safety measure in case there are already duplicate records
        connection = op.get_bind()

        # Find and delete duplicate integrations, keeping the most recent one
        connection.execute(
            sa.text(
                """
            DELETE FROM integrations 
            WHERE id NOT IN (
                SELECT MAX(id) 
                FROM integrations 
                GROUP BY user_id, provider
            )
        """
            )
        )

        # Add unique constraint on user_id and provider combination
        batch_op.create_unique_constraint(
            "uq_integrations_user_provider", ["user_id", "provider"]
        )


def downgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("integrations") as batch_op:
        # Remove the unique constraint
        batch_op.drop_constraint("uq_integrations_user_provider", type_="unique")
