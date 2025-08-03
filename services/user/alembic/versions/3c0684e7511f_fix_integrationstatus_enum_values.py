"""fix_integrationstatus_enum_values

Revision ID: 3c0684e7511f
Revises: 7e17b554456e
Create Date: 2025-08-02 20:50:48.490194

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c0684e7511f'
down_revision = '7e17b554456e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the database dialect to handle different database types
    connection = op.get_bind()
    dialect = connection.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL: Fix the enum values to match Python enum (lowercase)
        # Add the missing 'expired' value (lowercase to match Python enum)
        op.execute("ALTER TYPE integrationstatus ADD VALUE 'expired'")
        
        # Update any existing records to use lowercase values to match Python enum
        op.execute("UPDATE integrations SET status = 'active' WHERE status = 'ACTIVE'")
        op.execute("UPDATE integrations SET status = 'inactive' WHERE status = 'INACTIVE'")
        op.execute("UPDATE integrations SET status = 'error' WHERE status = 'ERROR'")
        op.execute("UPDATE integrations SET status = 'pending' WHERE status = 'PENDING'")
        
        # Note: We can't easily remove the uppercase values from the enum in PostgreSQL
        # without recreating the entire enum, which is complex and risky.
        # The lowercase values will work correctly with the Python code.
        
    elif dialect == 'sqlite':
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
