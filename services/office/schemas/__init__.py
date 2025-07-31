from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from services.office.models import Provider

T = TypeVar("T")


# Unified Email Models
class EmailAddress(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    name: Optional[str] = Field(None, max_length=100, description="Display name")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate that name is not empty if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty string to None
        return v.strip() if v else v


class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = []
    cc_addresses: List[EmailAddress] = []
    bcc_addresses: List[EmailAddress] = []
    date: datetime
    labels: List[str] = []
    is_read: bool = False
    has_attachments: bool = False
    # Provenance Information
    provider: Provider
    provider_message_id: str
    account_email: EmailStr  # Which account this message belongs to
    account_name: Optional[str] = None  # Display name for the account


class EmailThread(BaseModel):
    id: str
    subject: Optional[str] = None
    messages: List[EmailMessage]
    participant_count: int
    last_message_date: datetime
    is_read: bool = False
    providers: List[Provider]


class Conversation(BaseModel):
    """Microsoft Graph conversation/thread model."""
    
    id: str = Field(..., description="Microsoft Graph conversation ID")
    topic: Optional[str] = Field(None, description="Conversation topic/subject")
    has_attachments: bool = Field(False, description="Whether conversation has attachments")
    last_delivered_date_time: Optional[datetime] = Field(None, description="Last delivered message time")
    unique_senders: List[str] = Field(default_factory=list, description="Unique sender email addresses")
    preview: Optional[str] = Field(None, description="Preview of the conversation")


class EmailThreadList(BaseModel):
    """Response model for email thread lists."""
    
    success: bool
    data: Optional[Dict[str, Any]] = None  # Contains threads, metadata, etc.
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class SendEmailRequest(BaseModel):
    """Request model for sending emails."""

    to: List[EmailAddress]
    subject: str
    body: str
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    reply_to_message_id: Optional[str] = None
    provider: Optional[str] = None  # If not specified, uses user's default preference
    importance: Optional[str] = None  # "high", "normal", "low"


class SendEmailResponse(BaseModel):
    """Response model for sending emails."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str


class EmailMessageList(BaseModel):
    """Response model for email message lists."""

    success: bool
    data: Optional[Dict[str, Any]] = None  # Contains messages, metadata, etc.
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class EmailFolder(BaseModel):
    """Model for email folders/labels."""

    label: str = Field(..., description="Unique identifier for the folder/label")
    name: str = Field(..., description="Display name for the folder/label")
    provider: Provider = Field(..., description="Provider this folder belongs to")
    provider_folder_id: Optional[str] = Field(
        None, description="Provider-specific folder ID"
    )
    account_email: EmailStr = Field(
        ..., description="Which account this folder belongs to"
    )
    account_name: Optional[str] = Field(
        None, description="Display name for the account"
    )
    is_system: bool = Field(
        False, description="Whether this is a system folder (inbox, sent, etc.)"
    )
    message_count: Optional[int] = Field(
        None, description="Number of messages in this folder"
    )


class EmailFolderList(BaseModel):
    """Response model for email folder lists."""

    success: bool
    data: Optional[Dict[str, Any]] = None  # Contains folders, metadata, etc.
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


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


# Unified File Models
class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: datetime
    modified_time: datetime
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None
    thumbnail_link: Optional[str] = None
    parent_folder_id: Optional[str] = None
    is_folder: bool = False
    # Provenance Information
    provider: Provider
    provider_file_id: str
    account_email: EmailStr  # Which account this file belongs to
    account_name: Optional[str] = None  # Display name for the account


class DriveFileList(BaseModel):
    """Response model for drive file lists."""

    success: bool
    data: Optional[List[DriveFile]] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


# API Response Models
class BaseApiResponse(BaseModel):
    """Base response model with common fields."""

    success: bool
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class ApiResponse(BaseApiResponse):
    """Generic API response for backward compatibility."""

    data: Optional[Any] = None


class TypedApiResponse(BaseApiResponse, Generic[T]):
    """Generic typed API response."""

    data: Optional[T] = None


# Availability Models
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


class AvailableSlot(BaseModel):
    """Model for an available time slot."""

    start: datetime
    end: datetime
    duration_minutes: int


class AvailabilityResponse(BaseModel):
    """Response model for availability checks."""

    available_slots: List[AvailableSlot]
    total_slots: int
    time_range: Dict[str, str]  # start and end times
    providers_used: List[str]
    provider_errors: Optional[Dict[str, str]] = None
    request_metadata: Dict[str, Any]


# Calendar Event Response Models
class CalendarEventResponse(BaseModel):
    """Response model for calendar event operations."""

    event_id: Optional[str] = None
    provider: str
    status: str  # created, updated, deleted
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    request_metadata: Dict[str, Any]


class PaginatedResponse(BaseModel):
    items: List[Any]
    total_count: Optional[int] = None
    next_page_token: Optional[str] = None
    has_more: bool = False


# Error Models
class ApiError(BaseModel):
    type: str  # "validation_error", "auth_error", "provider_error", etc.
    message: str
    details: Optional[Dict[str, Any]] = None
    provider: Optional[Provider] = None
    retry_after: Optional[int] = None  # seconds
    request_id: str


# Health Check Models
class HealthCheck(BaseModel):
    """Response model for health checks."""

    status: str
    timestamp: datetime
    checks: Dict[str, Any]


class IntegrationHealthCheck(BaseModel):
    """Response model for integration health checks."""

    user_id: str
    integrations: Dict[str, Dict[str, Any]]


# Type aliases for common response types
AvailabilityApiResponse = TypedApiResponse[AvailabilityResponse]
CalendarEventApiResponse = TypedApiResponse[CalendarEventResponse]
CalendarEventListApiResponse = TypedApiResponse[List[CalendarEvent]]
EmailMessageListApiResponse = TypedApiResponse[List[EmailMessage]]
DriveFileListApiResponse = TypedApiResponse[List[DriveFile]]
