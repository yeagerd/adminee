from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from services.common.logging_config import get_logger
from services.meetings.models.meeting import MeetingType

# Configure logging
logger = get_logger(__name__)


class TimeSlotBase(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str


class TimeSlotCreate(TimeSlotBase):
    pass


class TimeSlot(TimeSlotBase):
    id: UUID
    is_available: bool
    model_config = ConfigDict(from_attributes=True)


class PollParticipantBase(BaseModel):
    email: EmailStr
    name: Optional[str]


class PollParticipantCreate(PollParticipantBase):
    poll_id: Optional[UUID] = None
    response_token: Optional[str] = None


class PollParticipant(PollParticipantBase):
    id: UUID
    status: str
    invited_at: datetime
    responded_at: Optional[datetime]
    reminder_sent_count: int
    response_token: str
    model_config = ConfigDict(from_attributes=True)


class PollResponseBase(BaseModel):
    time_slot_id: UUID
    response: str
    comment: Optional[str]


class PollResponseCreate(PollResponseBase):
    pass


class PollResponse(PollResponseBase):
    id: UUID
    participant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MeetingPollBase(BaseModel):
    title: str
    description: Optional[str]
    duration_minutes: int
    location: Optional[str]
    meeting_type: MeetingType
    response_deadline: Optional[datetime]
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None
    reveal_participants: Optional[bool] = False
    send_emails: Optional[bool] = False

    @field_validator("meeting_type", mode="before")
    @classmethod
    def validate_meeting_type(cls, v: Any) -> MeetingType:
        """Validate and normalize meeting_type values to ensure they're always MeetingType."""
        if isinstance(v, MeetingType):
            return v

        # Handle string values
        if isinstance(v, str):
            v_lower = v.lower().strip()
            # Map common variations to valid enum values
            if v_lower in ["test", "unknown", ""]:
                logger.warning(
                    "Invalid meeting_type value encountered",
                    original_value=v,
                    normalized_to="tbd",
                    reason="invalid_value",
                )
                return MeetingType.tbd
            try:
                return MeetingType(v_lower)
            except ValueError:
                # If it's not a valid enum value, default to tbd
                logger.warning(
                    "Invalid meeting_type value encountered",
                    original_value=v,
                    normalized_to="tbd",
                    reason="not_in_enum",
                )
                return MeetingType.tbd

        # For any other type, default to tbd
        logger.warning(
            "Invalid meeting_type value encountered",
            original_value=str(v),
            normalized_to="tbd",
            reason="wrong_type",
        )
        return MeetingType.tbd


class MeetingPollCreate(MeetingPollBase):
    time_slots: List[TimeSlotCreate]
    participants: List[PollParticipantCreate]


class MeetingPollUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_type: Optional[MeetingType] = None
    response_deadline: Optional[datetime] = None
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None
    reveal_participants: Optional[bool] = None

    @field_validator("meeting_type", mode="before")
    @classmethod
    def validate_meeting_type(cls, v: Any) -> Optional[MeetingType]:
        """Validate and normalize meeting_type values to ensure they're always MeetingType."""
        if v is None:
            return v

        if isinstance(v, MeetingType):
            return v

        # Handle string values
        if isinstance(v, str):
            v_lower = v.lower().strip()
            try:
                return MeetingType(v_lower)
            except ValueError:
                # If it's not a valid enum value, default to tbd
                logger.warning(
                    "Invalid meeting_type value encountered in update",
                    original_value=v,
                    normalized_to="tbd",
                    reason="not_in_enum",
                )
                return MeetingType.tbd

        # For any other type, default to tbd
        logger.warning(
            "Invalid meeting_type value encountered",
            original_value=str(v),
            normalized_to="tbd",
            reason="wrong_type",
        )
        return MeetingType.tbd


class MeetingPoll(MeetingPollBase):
    id: UUID
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    poll_token: str
    time_slots: List[TimeSlot]
    participants: List[PollParticipant]
    responses: Optional[List[PollResponse]] = None
    model_config = ConfigDict(from_attributes=True)


class ChatMeetingBase(BaseModel):
    chat_message: str
    extracted_intent: Optional[str]


class ChatMeetingCreate(ChatMeetingBase):
    pass


class ChatMeeting(ChatMeetingBase):
    id: UUID
    user_id: str
    poll_id: Optional[UUID]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
