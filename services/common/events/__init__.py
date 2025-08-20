"""
Event schemas for PubSub messages used across Briefly services.

This module provides Pydantic models for all PubSub events to ensure
type safety and consistency across services.
"""

from .base_events import BaseEvent, EventMetadata
from .email_events import (
    EmailData,
    EmailBackfillEvent,
    EmailUpdateEvent,
    EmailBatchEvent,
)
from .calendar_events import (
    CalendarEventData,
    CalendarUpdateEvent,
    CalendarBatchEvent,
)
from .contact_events import (
    ContactData,
    ContactUpdateEvent,
    ContactBatchEvent,
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
