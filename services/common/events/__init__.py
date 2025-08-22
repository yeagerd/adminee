"""
Event schemas for PubSub messages used across Briefly services.

This module provides Pydantic models for all PubSub events to ensure
type safety and consistency across services.
"""

from .base_events import BaseEvent, EventMetadata
from .calendar_events import (
    CalendarBatchEvent,
    CalendarEvent,
    CalendarEventData,
    CalendarUpdateEvent,
)
from .contact_events import (
    ContactBatchEvent,
    ContactData,
    ContactEvent,
    ContactUpdateEvent,
)
from .document_events import (
    DocumentData,
    DocumentEvent,
    DocumentFragmentData,
    DocumentFragmentEvent,
    PresentationDocumentData,
    SheetDocumentData,
    WordDocumentData,
)
from .email_events import (
    EmailBackfillEvent,
    EmailBatchEvent,
    EmailData,
    EmailEvent,
    EmailUpdateEvent,
)
from .internal_tool_events import (
    BookingData,
    BookingEvent,
    LLMChatEvent,
    LLMChatMessageData,
    MeetingPollData,
    MeetingPollEvent,
    ShipmentEvent,
    ShipmentEventData,
)
from .todo_events import (
    TodoData,
    TodoEvent,
    TodoListData,
    TodoListEvent,
)

__all__ = [
    # Base events
    "BaseEvent",
    "EventMetadata",
    # Email data and events
    "EmailData",
    "EmailEvent",
    "EmailBackfillEvent",  # Deprecated
    "EmailUpdateEvent",  # Deprecated
    "EmailBatchEvent",  # Deprecated
    # Calendar data and events
    "CalendarEventData",
    "CalendarEvent",
    "CalendarUpdateEvent",  # Deprecated
    "CalendarBatchEvent",  # Deprecated
    # Contact data and events
    "ContactData",
    "ContactEvent",
    "ContactUpdateEvent",  # Deprecated
    "ContactBatchEvent",  # Deprecated
    # Document data and events
    "DocumentData",
    "DocumentEvent",
    "DocumentFragmentData",
    "DocumentFragmentEvent",
    "WordDocumentData",
    "SheetDocumentData",
    "PresentationDocumentData",
    # Todo data and events
    "TodoData",
    "TodoEvent",
    "TodoListData",
    "TodoListEvent",
    # Internal tool events
    "LLMChatMessageData",
    "LLMChatEvent",
    "ShipmentEventData",
    "ShipmentEvent",
    "MeetingPollData",
    "MeetingPollEvent",
    "BookingData",
    "BookingEvent",
]
