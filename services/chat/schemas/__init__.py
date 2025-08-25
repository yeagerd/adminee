"""
Chat service schemas.

This module now imports from the shared API package.
"""

from services.api.v1.chat.office_responses import (
    CalendarToolResponse,
    OfficeServiceCalendarResponse,
    OfficeServiceErrorResponse,
)

__all__ = [
    "CalendarToolResponse",
    "OfficeServiceErrorResponse",
    "OfficeServiceCalendarResponse",
]
