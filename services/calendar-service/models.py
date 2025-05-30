# Pydantic models for Calendar Service API
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DateTimeTimeZone(BaseModel):
    dateTime: datetime
    timeZone: str

class Attendee(BaseModel):
    emailAddress: dict # Simplified, could be nested model e.g. class EmailAddress(BaseModel): address: str; name: Optional[str]
    type: Optional[str] = None # "required", "optional", "resource"

class Organizer(BaseModel):
    emailAddress: dict # Simplified

class CalendarEvent(BaseModel):
    id: str
    subject: Optional[str] = None
    bodyPreview: Optional[str] = None
    body: Optional[dict] = None # e.g. { "contentType": "HTML", "content": "..." }
    start: DateTimeTimeZone
    end: DateTimeTimeZone
    isAllDay: Optional[bool] = False
    isCancelled: Optional[bool] = False
    organizer: Optional[Organizer] = None
    attendees: Optional[List[Attendee]] = Field(default_factory=list)
    webLink: Optional[str] = None
    location: Optional[dict] = None # e.g. { "displayName": "Conference Room" }
    locations: Optional[List[dict]] = Field(default_factory=list) # For multiple locations

class CalendarEventResponse(BaseModel):
    value: List[CalendarEvent]

class ConflictingEventPair(BaseModel):
    event1_id: str
    event1_subject: Optional[str] = None
    event1_start: datetime # Store actual datetime for easier comparison/display
    event1_end: datetime
    
    event2_id: str
    event2_subject: Optional[str] = None
    event2_start: datetime
    event2_end: datetime
    
    overlap_minutes: Optional[float] = None # Could be calculated and added

class ConflictDetectionResult(BaseModel):
    conflicts: List[ConflictingEventPair] = Field(default_factory=list)
    checked_event_count: int
    conflict_pair_count: int

# AnalysisResult could be a more generic wrapper later if needed
# class AnalysisResult(BaseModel):
#     conflict_analysis: Optional[ConflictDetectionResult] = None
#     # other_analysis_types...

# This file will contain models for:
# - CalendarEvent
# - AnalysisResult
# etc. 