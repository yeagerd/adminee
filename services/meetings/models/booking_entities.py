import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON

from services.meetings.models.base import Base


class BookingTemplate(Base):
    __tablename__ = "booking_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    questions = Column(JSON, nullable=True)
    email_followup_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BookingLink(Base):
    __tablename__ = "booking_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id = Column(String(255), nullable=False)
    slug = Column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings = Column(JSON, nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("booking_templates.id"))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OneTimeLink(Base):
    __tablename__ = "one_time_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    booking_link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("booking_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_email = Column(String(255), nullable=False)
    token = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    link_id = Column(
        UUID(as_uuid=True), ForeignKey("booking_links.id", ondelete="SET NULL")
    )
    one_time_link_id = Column(
        UUID(as_uuid=True), ForeignKey("one_time_links.id", ondelete="SET NULL")
    )
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    attendee_email = Column(String(255), nullable=False)
    answers = Column(JSON, nullable=True)
    calendar_event_id = Column(String(255))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("one_time_link_id", name="_one_time_link_single_use_uc"),
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("booking_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(32), nullable=False)  # view | booked
    occurred_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    referrer = Column(String(512))
