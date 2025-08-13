"""add_bookings_tables

Revision ID: 8c4a1b9d2f31
Revises: 7f6c3a9b3e7a
Create Date: 2025-08-13 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8c4a1b9d2f31"
down_revision = "7f6c3a9b3e7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # booking_templates
    op.create_table(
        "booking_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=True),
        sa.Column("email_followup_enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # booking_links
    op.create_table(
        "booking_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["booking_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # one_time_links
    op.create_table(
        "one_time_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_link_id", sa.UUID(), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_link_id"], ["booking_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    # bookings
    op.create_table(
        "bookings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("link_id", sa.UUID(), nullable=True),
        sa.Column("one_time_link_id", sa.UUID(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attendee_email", sa.String(length=255), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("calendar_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["link_id"], ["booking_links.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["one_time_link_id"], ["one_time_links.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("one_time_link_id", name="_one_time_link_single_use_uc"),
    )

    # analytics_events
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("link_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("referrer", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["link_id"], ["booking_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("bookings")
    op.drop_table("one_time_links")
    op.drop_table("booking_links")
    op.drop_table("booking_templates")


