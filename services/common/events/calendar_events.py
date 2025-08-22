"""
Calendar event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent


class CalendarEventData(BaseModel):
    """Calendar event data structure."""

    id: str = Field(..., description="Unique calendar event ID")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    all_day: bool = Field(default=False, description="Whether this is an all-day event")
    location: Optional[str] = Field(None, description="Event location")
    organizer: str = Field(..., description="Event organizer email")
    attendees: List[str] = Field(
        default_factory=list, description="Attendee email addresses"
    )
    status: str = Field(
        default="confirmed",
        description="Event status (confirmed, tentative, cancelled)",
    )
    visibility: str = Field(
        default="default", description="Event visibility (default, public, private)"
    )
    provider: str = Field(..., description="Calendar provider (google, outlook, etc.)")
    provider_event_id: str = Field(..., description="Provider's internal event ID")
    calendar_id: str = Field(..., description="Calendar ID where the event is stored")

    # Additional metadata
    recurrence: Optional[Dict[str, Any]] = Field(None, description="Recurrence rules")
    reminders: List[Dict[str, Any]] = Field(
        default_factory=list, description="Reminder settings"
    )
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Event attachments"
    )
    color_id: Optional[str] = Field(None, description="Event color identifier")
    html_link: Optional[str] = Field(
        None, description="Link to view event in provider's UI"
    )


class CalendarEvent(BaseEvent):
    """Event for calendar operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the calendar operation")
    event: CalendarEventData = Field(..., description="Calendar event data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(None, description="Batch identifier for batch operations")
    last_updated: datetime = Field(..., description="When the event was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced from provider")
    provider: str = Field(..., description="Calendar provider (google, outlook, etc.)")
    calendar_id: str = Field(..., description="Calendar ID where the event is stored")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class CalendarUpdateEvent(BaseEvent):
    """Event for individual calendar event updates (deprecated - use CalendarEvent)."""

    user_id: str = Field(..., description="User ID for the calendar update")
    event: CalendarEventData = Field(..., description="Updated calendar event data")
    update_type: str = Field(..., description="Type of update (create, update, delete)")
    change_reason: Optional[str] = Field(None, description="Reason for the change")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class CalendarBatchEvent(BaseEvent):
    """Event for batch calendar operations (deprecated - use CalendarEvent with batch_id)."""

    user_id: str = Field(..., description="User ID for the batch operation")
    provider: str = Field(..., description="Calendar provider")
    events: List[CalendarEventData] = Field(
        ..., description="List of calendar events in the batch"
    )
    operation: str = Field(..., description="Operation type (sync, import, export)")
    batch_id: str = Field(..., description="Unique batch identifier")
    calendar_id: str = Field(..., description="Calendar ID being processed")

    # Time range for batch operations
    start_date: Optional[datetime] = Field(
        None, description="Start date for batch range"
    )
    end_date: Optional[datetime] = Field(None, description="End date for batch range")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"
