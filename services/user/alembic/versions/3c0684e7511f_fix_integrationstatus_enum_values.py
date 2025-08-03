"""fix_integrationstatus_enum_values

Revision ID: 3c0684e7511f
Revises: 7e17b554456e
Create Date: 2025-08-02 20:50:48.490194

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3c0684e7511f"
down_revision = "7e17b554456e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the database dialect to handle different database types
    connection = op.get_bind()
    dialect = connection.dialect.name

    if dialect == "postgresql":
        # PostgreSQL: Fix the enum values to match Python enum (lowercase)

        # First, add all lowercase enum values that might not exist
        # Use a function to check if value exists before adding (idempotent)
        def add_enum_value_if_not_exists(enum_name: str, value: str) -> None:
            # Check if the value already exists in the enum
            result = connection.execute(
                sa.text(
                    """
                    SELECT 1 FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = :enum_name)
                    AND enumlabel = :value
                    """
                ),
                {"enum_name": enum_name, "value": value},
            ).fetchone()

            if not result:
                # Value doesn't exist, add it
                connection.execute(
                    sa.text(f"ALTER TYPE {enum_name} ADD VALUE '{value}'")
                )

        # Add all lowercase values that the Python code expects
        add_enum_value_if_not_exists("integrationstatus", "active")
        add_enum_value_if_not_exists("integrationstatus", "inactive")
        add_enum_value_if_not_exists("integrationstatus", "error")
        add_enum_value_if_not_exists("integrationstatus", "pending")
        add_enum_value_if_not_exists("integrationstatus", "expired")

        # Now update existing records to use lowercase values
        # Only update if the record has uppercase values (safe to re-run)
        connection.execute(
            sa.text("UPDATE integrations SET status = 'active' WHERE status = 'ACTIVE'")
        )
        connection.execute(
            sa.text(
                "UPDATE integrations SET status = 'inactive' WHERE status = 'INACTIVE'"
            )
        )
        connection.execute(
            sa.text("UPDATE integrations SET status = 'error' WHERE status = 'ERROR'")
        )
        connection.execute(
            sa.text(
                "UPDATE integrations SET status = 'pending' WHERE status = 'PENDING'"
            )
        )

        # Note: We can't easily remove the uppercase values from the enum in PostgreSQL
        # without recreating the entire enum, which is complex and risky.
        # The lowercase values will work correctly with the Python code.

    elif dialect == "sqlite":
        # SQLite doesn't have native enums, so no action needed
        # The enum values are handled by the application layer
        pass
    else:
        # For other databases, we'll skip this migration
        # The enum values will be handled by the application layer
        pass


def downgrade() -> None:
    # Note: This migration is not easily reversible in PostgreSQL
    # because we can't remove enum values without recreating the enum
    # For now, we'll leave the changes in place during downgrade
    pass
