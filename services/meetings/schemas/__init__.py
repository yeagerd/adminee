"""
Meetings service schemas.

This module now imports from the shared API package.
"""

from services.api.v1.meetings.meetings import (
    ChatMeeting,
    ChatMeetingBase,
    ChatMeetingCreate,
    MeetingPoll,
    MeetingPollBase,
    MeetingPollCreate,
    MeetingPollUpdate,
    PollParticipant,
    PollParticipantBase,
    PollParticipantCreate,
    PollResponse,
    PollResponseBase,
    PollResponseCreate,
    TimeSlot,
    TimeSlotBase,
    TimeSlotCreate,
)

__all__ = [
    "ChatMeeting",
    "ChatMeetingBase",
    "ChatMeetingCreate",
    "MeetingPoll",
    "MeetingPollBase",
    "MeetingPollCreate",
    "MeetingPollUpdate",
    "PollParticipant",
    "PollParticipantBase",
    "PollParticipantCreate",
    "PollResponse",
    "PollResponseBase",
    "PollResponseCreate",
    "TimeSlot",
    "TimeSlotBase",
    "TimeSlotCreate",
]
