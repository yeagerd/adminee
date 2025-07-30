"""add unique constraint tracking number carrier

Revision ID: add_unique_constraint_tracking_number_carrier
Revises: e81c5b37dc1d
Create Date: 2025-01-30 05:20:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_unique_constraint_tracking_number_carrier"
down_revision = "e81c5b37dc1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint for user_id + tracking_number + carrier combination
    # This prevents duplicate packages for the same user with the same tracking number and carrier
    op.create_unique_constraint(
        "uq_package_user_tracking_carrier",
        "package",
        ["user_id", "tracking_number", "carrier"],
    )


def downgrade() -> None:
    # Remove the unique constraint
    op.drop_constraint("uq_package_user_tracking_carrier", "package", type_="unique")
