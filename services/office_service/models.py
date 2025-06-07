# Pydantic models for Calendar Service API
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EmailAddress(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = (
        None  # Address can sometimes be null for certain attendees/organizers
    )


class ResponseStatus(BaseModel):
    response: Optional[str] = (
        None  # e.g., "accepted", "declined", "tentativelyAccepted", "notResponded", "none"
    )
    time: Optional[datetime] = None


class DateTimeTimeZone(BaseModel):
    dateTime: datetime
    timeZone: str


class Attendee(BaseModel):
    emailAddress: Optional[EmailAddress] = (
        None  # Changed from dict to EmailAddress model
    )
    type: Optional[str] = None  # "required", "optional", "resource"
    status: Optional[ResponseStatus] = None  # Added status field


class Organizer(BaseModel):
    emailAddress: Optional[EmailAddress] = (
        None  # Changed from dict to EmailAddress model
    )


class CalendarEvent(BaseModel):
    id: str
    subject: Optional[str] = None
    bodyPreview: Optional[str] = None
    body: Optional[dict] = None  # e.g. { "contentType": "HTML", "content": "..." }
    start: DateTimeTimeZone
    end: DateTimeTimeZone
    isAllDay: Optional[bool] = False
    isCancelled: Optional[bool] = False
    organizer: Optional[Organizer] = None
    attendees: List[Attendee] = Field(
        default_factory=list
    )  # Ensure it's List, not Optional[List]
    webLink: Optional[str] = None
    location: Optional[dict] = None  # e.g. { "displayName": "Conference Room" }
    locations: List[dict] = Field(default_factory=list)  # For multiple locations


class CalendarEventResponse(BaseModel):
    value: List[CalendarEvent]


class ConflictingEventPair(BaseModel):
    event1_id: str
    event1_subject: Optional[str] = None
    event1_start: datetime  # Store actual datetime for easier comparison/display
    event1_end: datetime

    event2_id: str
    event2_subject: Optional[str] = None
    event2_start: datetime
    event2_end: datetime

    overlap_minutes: Optional[float] = None  # Could be calculated and added


class ConflictDetectionResult(BaseModel):
    conflicts: List[ConflictingEventPair] = Field(default_factory=list)
    checked_event_count: int
    conflict_pair_count: int


# Models for revised attendance analysis (Task 3.4)
class AttendeeStatusEnum(str, Enum):
    ACCEPTED = "accepted"
    TENTATIVELY_ACCEPTED = "tentativelyAccepted"
    DECLINED = "declined"
    NOT_RESPONDED = "notResponded"
    NONE = (
        "none"  # For organizer or if status is genuinely missing/unknown from provider
    )
    UNKNOWN = "unknown"  # If provider gives a status we don't map


class AnalyzedAttendee(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None  # Email address is primary identifier
    attendee_type: Optional[str] = None  # 'required', 'optional', 'resource'
    response_status: AttendeeStatusEnum = AttendeeStatusEnum.NONE
    response_time: Optional[datetime] = None


class EventAttendanceDetail(BaseModel):
    event_id: str
    event_subject: Optional[str] = None
    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None
    attendees: List[AnalyzedAttendee] = Field(default_factory=list)
    # Optional summary counts can be added here if needed e.g.:
    # count_required_accepted: int
    # count_required_declined: int
    # ...etc.


# Models for work hours conflict detection (Task 3.5)
class WorkDay(BaseModel):
    start_time: Optional[str] = Field(
        None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$"
    )  # HH:MM format
    end_time: Optional[str] = Field(
        None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$"
    )  # HH:MM format
    is_working_day: bool = False


class UserWorkHours(BaseModel):
    # Using 0 for Monday, 6 for Sunday, aligning with datetime.weekday()
    monday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    tuesday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    wednesday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    thursday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    friday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    saturday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    sunday: WorkDay = Field(
        default_factory=lambda: WorkDay(
            start_time=None, end_time=None, is_working_day=False
        )
    )
    # Timezone is crucial and must be provided alongside events which are in specific timezones
    # It will be used to interpret the start_time/end_time strings correctly.
    # The events themselves already have timezone info in their start/end DateTimeTimeZone objects.


class WorkHoursConflictInfo(BaseModel):
    event_id: str
    event_subject: Optional[str] = None
    is_outside_work_hours: bool
    conflict_details: Optional[str] = (
        None  # e.g., "Starts before work hours", "Ends after work hours", "During non-working day"
    )


class WorkHoursConflictResult(BaseModel):
    conflicts: List[WorkHoursConflictInfo] = Field(default_factory=list)
    checked_event_count: int


# Old AttendanceMetrics and EventAttendanceAnalysis are effectively replaced by EventAttendanceDetail
# class AttendanceMetrics(BaseModel): ...
# class EventAttendanceAnalysis(BaseModel): ...

# This will hold analyses for a list of events later if needed
# class BulkAttendanceAnalysisResult(BaseModel):
#     analyses: List[EventAttendanceAnalysis]
#     analyzed_event_count: int

# AnalysisResult could be a more generic wrapper later if needed
# class AnalysisResult(BaseModel):
#     conflict_analysis: Optional[ConflictDetectionResult] = None
#     # other_analysis_types...

# This file will contain models for:
# - CalendarEvent
# - AnalysisResult
# etc.
