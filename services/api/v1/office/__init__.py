"""
Office service API schemas.
"""

from services.api.v1.office import calendar, contacts, email, files, models, responses
from services.api.v1.office.responses import (
    ApiResponse,
    AvailabilityApiResponse,
    AvailabilityResponse,
    AvailableSlot,
    BaseApiResponse,
    CalendarEventApiResponse,
    CalendarEventDetailResponse,
    CalendarEventListApiResponse,
    CalendarEventResponse,
    ContactResponse,
    ContactsListApiResponse,
    DriveFileListApiResponse,
    DriveFileResponse,
    EmailMessageListApiResponse,
    EmailMessageResponse,
    TimeRange,
    TypedApiResponse,
)

__all__ = [
    "calendar",
    "contacts",
    "email",
    "files",
    "models",
    "responses",
    "ApiResponse",
    "AvailabilityApiResponse",
    "PaginatedResponse",
    "AvailabilityResponse",
    "AvailableSlot",
    "BaseApiResponse",
    "CalendarEventApiResponse",
    "CalendarEventDetailResponse",
    "CalendarEventListApiResponse",
    "CalendarEventResponse",
    "ContactResponse",
    "ContactsListApiResponse",
    "DriveFileListApiResponse",
    "DriveFileResponse",
    "FileDetailResponse",
    "FileListResponse",
    "FileSearchResponse",
    "EmailMessageListApiResponse",
    "EmailMessageResponse",
    "TimeRange",
    "TypedApiResponse",
]
