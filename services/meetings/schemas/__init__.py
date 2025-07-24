from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TimeSlotBase(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str


class TimeSlotCreate(TimeSlotBase):
    pass


class TimeSlot(TimeSlotBase):
    id: UUID
    is_available: bool

    class Config:
        orm_mode = True


class PollParticipantBase(BaseModel):
    email: EmailStr
    name: Optional[str]


class PollParticipantCreate(PollParticipantBase):
    pass


class PollParticipant(PollParticipantBase):
    id: UUID
    status: str
    invited_at: datetime
    responded_at: Optional[datetime]
    reminder_sent_count: int

    class Config:
        orm_mode = True


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

    class Config:
        orm_mode = True


class MeetingPollBase(BaseModel):
    title: str
    description: Optional[str]
    duration_minutes: int
    location: Optional[str]
    meeting_type: str
    response_deadline: Optional[datetime]
    min_participants: Optional[int]
    max_participants: Optional[int]
    allow_anonymous_responses: Optional[bool]


class MeetingPollCreate(MeetingPollBase):
    time_slots: List[TimeSlotCreate]
    participants: List[PollParticipantCreate]


class MeetingPoll(MeetingPollBase):
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    poll_token: str
    time_slots: List[TimeSlot]
    participants: List[PollParticipant]

    class Config:
        orm_mode = True


class ChatMeetingBase(BaseModel):
    chat_message: str
    extracted_intent: Optional[str]


class ChatMeetingCreate(ChatMeetingBase):
    pass


class ChatMeeting(ChatMeetingBase):
    id: UUID
    user_id: UUID
    poll_id: Optional[UUID]
    created_at: datetime

    class Config:
        orm_mode = True
