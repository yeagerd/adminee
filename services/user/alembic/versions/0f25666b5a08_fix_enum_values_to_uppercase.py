"""fix_enum_values_to_uppercase

This migration ensures enum values are uppercase to match SQLAlchemy's expected convention.
This is a consolidated migration that replaces the previous back-and-forth enum value changes.
It should be run using the DB_URL_USER_MIGRATIONS environment variable which uses the postgres admin user.

Revision ID: 0f25666b5a08
Revises: 7e17b554456e
Create Date: 2025-08-02 23:33:42.699701

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f25666b5a08"
down_revision = "7e17b554456e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the database dialect to handle different database types
    connection = op.get_bind()
    dialect = connection.dialect.name

    if dialect == "postgresql":
        # PostgreSQL: Change enum values from lowercase to uppercase

        # First, create a new enum type with uppercase values
        connection.execute(
            sa.text(
                "CREATE TYPE integrationstatus_new AS ENUM ('ACTIVE', 'INACTIVE', 'ERROR', 'PENDING', 'EXPIRED')"
            )
        )

        # Update the column to use the new enum type
        # The USING clause will convert existing lowercase values to uppercase
        connection.execute(
            sa.text(
                "ALTER TABLE integrations ALTER COLUMN status TYPE integrationstatus_new USING UPPER(status::text)::integrationstatus_new"
            )
        )

        # Drop the old enum type
        connection.execute(sa.text("DROP TYPE integrationstatus"))

        # Rename the new enum type to the original name
        connection.execute(
            sa.text("ALTER TYPE integrationstatus_new RENAME TO integrationstatus")
        )

    elif dialect == "sqlite":
        # SQLite doesn't have native enums, so no action needed
        pass
    else:
        # For other databases, we'll skip this migration
        pass


def downgrade() -> None:
    # Note: This migration is not easily reversible in PostgreSQL
    # because we can't easily restore the lowercase values
    # For now, we'll leave the changes in place during downgrade
    pass
