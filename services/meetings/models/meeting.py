import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.meetings.models.base import Base


class MeetingType(str, enum.Enum):
    in_person = "in_person"
    virtual = "virtual"
    tbd = "tbd"


class PollStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"
    scheduled = "scheduled"


class ParticipantStatus(str, enum.Enum):
    pending = "pending"
    responded = "responded"
    declined = "declined"


class ResponseType(str, enum.Enum):
    available = "available"
    unavailable = "unavailable"
    maybe = "maybe"


class MeetingPoll(Base):
    __tablename__ = "meeting_polls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False)
    location = Column(String(500))
    meeting_type: Mapped[MeetingType] = mapped_column(
        Enum(MeetingType), default=MeetingType.tbd
    )
    status: Mapped[PollStatus] = mapped_column(
        Enum(PollStatus), default=PollStatus.draft
    )
    response_deadline = Column(DateTime(timezone=True))
    min_participants = Column(Integer, default=1)
    max_participants = Column(Integer)
    reveal_participants = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    scheduled_slot_id = Column(UUID(as_uuid=True), ForeignKey("time_slots.id"))
    poll_token = Column(String(64), unique=True, nullable=False)

    time_slots = relationship(
        "TimeSlot",
        back_populates="poll",
        cascade="all, delete-orphan",
        foreign_keys="[TimeSlot.poll_id]",
    )
    participants = relationship(
        "PollParticipant", back_populates="poll", cascade="all, delete-orphan"
    )


class TimeSlot(Base):
    __tablename__ = "time_slots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meeting_polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    poll = relationship(
        "MeetingPoll", back_populates="time_slots", foreign_keys="[TimeSlot.poll_id]"
    )
    responses = relationship(
        "PollResponse", back_populates="time_slot", cascade="all, delete-orphan"
    )


class PollParticipant(Base):
    __tablename__ = "poll_participants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meeting_polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus), default=ParticipantStatus.pending
    )
    invited_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    responded_at = Column(DateTime(timezone=True))
    reminder_sent_count = Column(Integer, default=0)
    response_token = Column(String(64), unique=True, nullable=False)

    poll = relationship("MeetingPoll", back_populates="participants")
    responses = relationship(
        "PollResponse", back_populates="participant", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("poll_id", "email", name="_poll_email_uc"),)


class PollResponse(Base):
    __tablename__ = "poll_responses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meeting_polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("poll_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    time_slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("time_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    response: Mapped[ResponseType] = mapped_column(Enum(ResponseType), nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    participant = relationship("PollParticipant", back_populates="responses")
    time_slot = relationship("TimeSlot", back_populates="responses")

    __table_args__ = (
        UniqueConstraint("participant_id", "time_slot_id", name="_participant_slot_uc"),
    )


class ChatMeeting(Base):
    __tablename__ = "chat_meetings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    chat_message = Column(Text, nullable=False)
    extracted_intent = Column(Text)  # Store as JSON string
    poll_id = Column(UUID(as_uuid=True), ForeignKey("meeting_polls.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
