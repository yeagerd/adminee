"""drop_old_package_id_column

Revision ID: f440e0ea1612
Revises: e093428e4407
Create Date: 2025-08-01 23:18:09.765454

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f440e0ea1612"
down_revision: Union[str, Sequence[str], None] = "e093428e4407"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The old_package_id column was manually dropped using SQL:
    # ALTER TABLE trackingevent DROP COLUMN old_package_id;
    # This migration is kept for record-keeping purposes.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the old_package_id column (though this would break existing data)
    # This is included for completeness but should not be used in practice
    op.add_column(
        "trackingevent", sa.Column("old_package_id", sa.Integer(), nullable=True)
    )
