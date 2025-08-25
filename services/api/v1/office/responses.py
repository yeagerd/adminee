"""
Office service API response models.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

from services.api.v1.office.models import Provider

T = TypeVar("T")


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


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""

    items: List[Any]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class TypedApiResponse(BaseApiResponse, Generic[T]):
    """Generic typed API response."""

    data: Optional[T] = None


# Availability Response Models
class AvailableSlot(BaseModel):
    """Model for an available time slot."""

    start: str
    end: str
    duration_minutes: int


class TimeRange(BaseModel):
    """Model for time range with start and end times."""

    start: str
    end: str


class AvailabilityResponse(BaseModel):
    """Response model for availability checks."""

    available_slots: list[AvailableSlot]
    total_slots: int
    time_range: TimeRange
    duration_minutes: int
    providers_checked: list[str]
    cache_hit: bool = False


# Calendar Response Models
class CalendarEventResponse(BaseModel):
    """Response model for calendar event operations."""

    event_id: str
    calendar_id: str
    provider: str
    status: str
    created_at: str
    updated_at: str


class CalendarEventDetailResponse(BaseModel):
    """Response model for detailed calendar event operations."""

    event_id: str
    calendar_id: str
    provider: str
    status: str
    created_at: str
    updated_at: str


# Email Response Models
class EmailMessageResponse(BaseModel):
    """Response model for email message operations."""

    message_id: str
    thread_id: str
    provider: str
    status: str
    created_at: str
    updated_at: str


# File Response Models
class DriveFileResponse(BaseModel):
    """Response model for drive file operations."""

    file_id: str
    parent_id: Optional[str] = None
    provider: str
    status: str
    created_at: str
    updated_at: str


class FileDetailResponse(BaseModel):
    """Response model for file detail operations."""

    file_id: str
    parent_id: Optional[str] = None
    provider: str
    status: str
    created_at: str
    updated_at: str


class FileListResponse(BaseModel):
    """Response model for file list operations."""

    files: list[DriveFileResponse]
    total_count: int
    providers_checked: list[str]
    cache_hit: bool = False


class FileSearchResponse(BaseModel):
    """Response model for file search operations."""

    files: list[DriveFileResponse]
    total_count: int
    query: str
    providers_checked: list[str]
    cache_hit: bool = False


# Contact Response Models
class ContactResponse(BaseModel):
    """Response model for contact operations."""

    contact_id: str
    provider: str
    status: str
    created_at: str
    updated_at: str


# Typed Response Aliases
AvailabilityApiResponse = TypedApiResponse[AvailabilityResponse]
CalendarEventApiResponse = TypedApiResponse[CalendarEventResponse]
CalendarEventListApiResponse = TypedApiResponse[list["CalendarEventResponse"]]
EmailMessageListApiResponse = TypedApiResponse[list["EmailMessageResponse"]]
DriveFileListApiResponse = TypedApiResponse[list["DriveFileResponse"]]
ContactsListApiResponse = TypedApiResponse[list["ContactResponse"]]
