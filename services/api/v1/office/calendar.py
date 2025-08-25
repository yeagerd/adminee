"""
Office service calendar schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

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


class AvailabilityRequest(BaseModel):
    """Request model for availability checks."""

    start: str = Field(
        ..., description="Start time for availability check (ISO format)"
    )
    end: str = Field(..., description="End time for availability check (ISO format)")
    duration: int = Field(
        ..., description="Duration in minutes for the meeting", ge=1, le=1440
    )  # Max 24 hours
    providers: Optional[List[str]] = Field(
        None,
        description="Providers to check (google, microsoft). If not specified, checks all available providers",
    )

    @field_validator("start", "end")
    @classmethod
    def validate_datetime_format(cls, v: str) -> str:
        """Validate that datetime strings are in ISO format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("datetime must be in ISO format (YYYY-MM-DDTHH:MM:SS)")

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate provider values."""
        if v is not None:
            valid_providers = ["google", "microsoft"]
            for provider in v:
                if provider.lower() not in valid_providers:
                    raise ValueError(
                        f'provider must be one of: {", ".join(valid_providers)}'
                    )
            return [p.lower() for p in v]
        return v

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "AvailabilityRequest":
        """Validate that end time is after start time."""
        try:
            start_dt = datetime.fromisoformat(self.start)
            end_dt = datetime.fromisoformat(self.end)
            if end_dt <= start_dt:
                raise ValueError("end time must be after start time")
        except (ValueError, TypeError) as e:
            # If datetime parsing fails, let the other validator handle it
            if "end time must be after start time" in str(e):
                raise
        return self


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


__all__ = [
    "AvailabilityRequest",
    "Calendar",
    "CalendarEvent",
    "CalendarEventList",
    "CalendarList",
    "CreateCalendarEventRequest",
    "CreateCalendarEventResponse",
    "FreeBusyInfo",
    "FreeBusyRequest",
    "FreeBusyResponse",
]
