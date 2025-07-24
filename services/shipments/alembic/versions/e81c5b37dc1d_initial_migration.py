"""
Revision ID: e81c5b37dc1d
Revises:
Create Date: 2025-07-24 00:25:37.638014
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e81c5b37dc1d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "package",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, index=True),
        sa.Column("tracking_number", sa.String(255), nullable=False),
        sa.Column("carrier", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("estimated_delivery", sa.Date),
        sa.Column("actual_delivery", sa.Date),
        sa.Column("recipient_name", sa.String(255)),
        sa.Column("recipient_address", sa.Text),
        sa.Column("shipper_name", sa.String(255)),
        sa.Column("package_description", sa.Text),
        sa.Column("order_number", sa.String(255)),
        sa.Column("tracking_link", sa.String(500)),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("archived_at", sa.DateTime),
        sa.Column("email_message_id", sa.String(255)),
    )
    op.create_index("ix_package_user_id", "package", ["user_id"])

    op.create_table(
        "label",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), default="#3B82F6"),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_label_user_id", "label", ["user_id"])

    op.create_table(
        "packagelabel",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("package_id", sa.Integer),
        sa.Column("label_id", sa.Integer),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "trackingevent",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("package_id", sa.Integer),
        sa.Column("event_date", sa.DateTime, nullable=False),
        sa.Column("status", sa.String(100), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "carrierconfig",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("carrier_name", sa.String(50), nullable=False),
        sa.Column("api_endpoint", sa.String(255)),
        sa.Column("rate_limit_per_hour", sa.Integer, default=1000),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("email_patterns", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("carrierconfig")
    op.drop_table("trackingevent")
    op.drop_table("packagelabel")
    op.drop_table("label")
    op.drop_table("package")
