"""empty message

Revision ID: 7e17b554456e
Revises: 1bda244bb65d, auto_add_timezone_mode_manual_timezone
Create Date: 2025-07-23 19:03:00.257641

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e17b554456e'
down_revision = ('1bda244bb65d', 'auto_add_timezone_mode_manual_timezone')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
