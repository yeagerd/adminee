"""
Event schemas for PubSub messages used across Briefly services.

This module provides Pydantic models for all PubSub events to ensure
type safety and consistency across services.
"""

from .base_events import BaseEvent, EventMetadata
from .calendar_events import (
    CalendarBatchEvent,
    CalendarEventData,
    CalendarUpdateEvent,
)
from .contact_events import (
    ContactBatchEvent,
    ContactData,
    ContactUpdateEvent,
)
from .email_events import (
    EmailBackfillEvent,
    EmailBatchEvent,
    EmailData,
    EmailUpdateEvent,
)

__all__ = [
    # Base events
    "BaseEvent",
    "EventMetadata",
    # Email data and events
    "EmailData",
    "EmailBackfillEvent",
    "EmailUpdateEvent",
    "EmailBatchEvent",
    # Calendar data and events
    "CalendarEventData",
    "CalendarUpdateEvent",
    "CalendarBatchEvent",
    # Contact data and events
    "ContactData",
    "ContactUpdateEvent",
    "ContactBatchEvent",
]
