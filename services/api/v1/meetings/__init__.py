"""
Meetings service API schemas.
"""

from services.api.v1.meetings import booking_requests, meetings
from services.api.v1.meetings.meetings import (
    ChatMeeting,
    ChatMeetingCreate,
    MeetingPoll,
    MeetingPollBase,
    MeetingPollCreate,
    MeetingPollUpdate,
    PollParticipant,
    PollParticipantCreate,
    PollResponse,
    PollResponseCreate,
    TimeSlot,
    TimeSlotCreate,
)

__all__ = [
    "booking_requests",
    "meetings",
    "MeetingPoll",
    "MeetingPollBase",
    "MeetingPollCreate",
    "MeetingPollUpdate",
    "TimeSlot",
    "TimeSlotCreate",
    "PollParticipant",
    "PollParticipantCreate",
    "PollResponse",
    "PollResponseCreate",
    "ChatMeeting",
    "ChatMeetingCreate",
]
