"""
Meetings service API schemas.
"""

from . import booking_requests, meetings
from .meetings import (
    MeetingPoll,
    MeetingPollBase,
    MeetingPollCreate,
    MeetingPollUpdate,
    TimeSlot,
    TimeSlotCreate,
    PollParticipant,
    PollParticipantCreate,
    PollResponse,
    PollResponseCreate,
    ChatMeeting,
    ChatMeetingCreate,
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
