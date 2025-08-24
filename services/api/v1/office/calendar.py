"""
Office service calendar schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from .email import EmailAddress
from .models import Provider


# Unified Calendar Models
class CalendarEvent(BaseModel):
    id: str
    calendar_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    attendees: List[EmailAddress] = []
    organizer: Optional[EmailAddress] = None
    status: str = "confirmed"  # confirmed, tentative, cancelled
    visibility: str = "default"  # default, public, private
    # Provenance Information
    provider: Provider
    provider_event_id: str
    account_email: EmailStr  # Which account this calendar belongs to
    account_name: Optional[str] = None  # Display name for the account
    calendar_name: str  # Name of the specific calendar
    created_at: datetime
    updated_at: datetime


class Calendar(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_primary: bool = False
    access_role: str  # owner, reader, writer, etc.
    # Provenance Information
    provider: Provider
    provider_calendar_id: str
    account_email: EmailStr  # Which account this calendar belongs to
    account_name: Optional[str] = None  # Display name for the account


class CreateCalendarEventRequest(BaseModel):
    """Request model for creating calendar events."""

    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(
        None, max_length=1000, description="Event description"
    )
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    all_day: bool = Field(False, description="Whether this is an all-day event")
    location: Optional[str] = Field(None, max_length=255, description="Event location")
    attendees: Optional[List[EmailAddress]] = Field(
        None, description="List of attendees"
    )
    calendar_id: Optional[str] = Field(
        None, description="Calendar ID (uses primary if not specified)"
    )
    provider: Optional[str] = Field(
        None, description="Provider preference (google, microsoft)"
    )
    visibility: Optional[str] = Field(
        "default", description="Event visibility (default, public, private)"
    )
    status: Optional[str] = Field(
        "confirmed", description="Event status (confirmed, tentative, cancelled)"
    )

    @field_validator("end_time")
    @classmethod
    def validate_end_time_after_start_time(
        cls, v: datetime, info: ValidationInfo
    ) -> datetime:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Validate that title is not empty or only whitespace."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        """Validate visibility value."""
        valid_values = ["default", "public", "private"]
        if v not in valid_values:
            raise ValueError(f'visibility must be one of: {", ".join(valid_values)}')
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        valid_values = ["confirmed", "tentative", "cancelled"]
        if v not in valid_values:
            raise ValueError(f'status must be one of: {", ".join(valid_values)}')
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider value."""
        if v is not None:
            valid_values = ["google", "microsoft"]
            if v.lower() not in valid_values:
                raise ValueError(f'provider must be one of: {", ".join(valid_values)}')
            return v.lower()
        return v


class CreateCalendarEventResponse(BaseModel):
    """Response model for creating calendar events."""

    success: bool
    data: Optional[CalendarEvent] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str


class CalendarEventList(BaseModel):
    """Response model for calendar event lists."""

    success: bool
    data: Optional[List[CalendarEvent]] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class FreeBusyInfo(BaseModel):
    calendar_id: str
    busy_times: List[Dict[str, datetime]]  # [{"start": datetime, "end": datetime}]
    # Provenance Information
    provider: Provider
    account_email: EmailStr  # Which account this calendar belongs to
    calendar_name: str  # Name of the specific calendar


class FreeBusyRequest(BaseModel):
    """Request model for checking free/busy time."""

    calendar_ids: List[str] = Field(..., description="List of calendar IDs to check")
    start_time: datetime = Field(..., description="Start time for free/busy check")
    end_time: datetime = Field(..., description="End time for free/busy check")
    provider: Optional[str] = Field(
        None, description="Provider preference (google, microsoft)"
    )

    @field_validator("end_time")
    @classmethod
    def validate_end_time_after_start_time(
        cls, v: datetime, info: ValidationInfo
    ) -> datetime:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class FreeBusyResponse(BaseModel):
    """Response model for free/busy time checks."""

    success: bool
    data: Optional[List[FreeBusyInfo]] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str


class CalendarList(BaseModel):
    """Response model for calendar lists."""

    success: bool
    data: Optional[List[Calendar]] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str
