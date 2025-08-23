"""
Event schemas for PubSub messages used across Briefly services.

This module provides Pydantic models for all PubSub events to ensure
type safety and consistency across services.
"""

from services.common.events.base_events import BaseEvent, EventMetadata
from services.common.events.calendar_events import (
    CalendarEvent,
    CalendarEventData,
)
from services.common.events.contact_events import (
    ContactData,
    ContactEvent,
)
from services.common.events.document_events import (
    DocumentData,
    DocumentEvent,
    DocumentFragmentData,
    DocumentFragmentEvent,
    PresentationDocumentData,
    SheetDocumentData,
    WordDocumentData,
)
from services.common.events.email_events import (
    EmailData,
    EmailEvent,
)
from services.common.events.internal_tool_events import (
    BookingData,
    BookingEvent,
    LLMChatEvent,
    LLMChatMessageData,
    MeetingPollData,
    MeetingPollEvent,
    ShipmentEvent,
    ShipmentEventData,
)
from services.common.events.todo_events import (
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
    # Calendar data and events
    "CalendarEventData",
    "CalendarEvent",
    # Contact data and events
    "ContactData",
    "ContactEvent",
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
