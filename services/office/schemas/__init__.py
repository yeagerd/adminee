from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr

from services.office.models import Provider


# Unified Email Models
class EmailAddress(BaseModel):
    email: EmailStr
    name: Optional[str] = None


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

    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    attendees: Optional[List[EmailAddress]] = None
    calendar_id: Optional[str] = None  # If not specified, uses primary calendar
    provider: Optional[str] = None  # If not specified, uses user's default preference
    visibility: Optional[str] = "default"  # default, public, private
    status: Optional[str] = "confirmed"  # confirmed, tentative, cancelled


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
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


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
