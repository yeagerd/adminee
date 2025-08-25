"""
Internal tool event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent



# LLM Chat Events
class LLMChatMessageData(BaseModel):
    """LLM chat message data structure."""

    id: str = Field(..., description="Unique message ID")
    chat_id: str = Field(..., description="Chat session ID")
    session_id: str = Field(..., description="User session ID")
    model_name: str = Field(..., description="LLM model used")
    role: str = Field(..., description="Message role (user, assistant, system)")
    message_type: str = Field(
        ..., description="Message type (text, tool_call, tool_result)"
    )
    content: str = Field(..., description="Message content")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    cost_usd: Optional[float] = Field(None, description="Cost in USD")
    tools_used: List[str] = Field(
        default_factory=list, description="Tools used in this message"
    )
    tool_results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tool execution results"
    )
    conversation_context: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation context"
    )
    user_feedback: Optional[str] = Field(
        None, description="User feedback on the response"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class LLMChatEvent(BaseEvent):
    """Event for LLM chat operations."""

    user_id: str = Field(..., description="User ID for the chat operation")
    message: LLMChatMessageData = Field(..., description="Chat message data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the message was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced")
    chat_id: str = Field(..., description="Chat session ID")
    session_id: str = Field(..., description="User session ID")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "chat-service"


# Shipment Events
class ShipmentEventData(BaseModel):
    """Shipment event data structure."""

    id: str = Field(..., description="Unique shipment event ID")
    shipment_id: str = Field(..., description="Shipment ID")
    tracking_number: str = Field(..., description="Tracking number")
    carrier: str = Field(..., description="Shipping carrier")
    event_type: str = Field(
        ..., description="Event type (created, shipped, delivered, etc.)"
    )
    event_timestamp: datetime = Field(..., description="When the event occurred")
    location: Optional[str] = Field(None, description="Event location")
    status: str = Field(..., description="Shipment status")
    description: str = Field(..., description="Event description")
    estimated_delivery: Optional[datetime] = Field(
        None, description="Estimated delivery date"
    )
    actual_delivery: Optional[datetime] = Field(
        None, description="Actual delivery date"
    )
    recipient_name: Optional[str] = Field(None, description="Recipient name")
    recipient_address: Optional[str] = Field(None, description="Recipient address")
    package_details: Dict[str, Any] = Field(
        default_factory=dict, description="Package details"
    )
    delivery_attempts: Optional[int] = Field(
        None, description="Number of delivery attempts"
    )
    signature_required: bool = Field(
        default=False, description="Whether signature is required"
    )
    signature_received: Optional[str] = Field(None, description="Signature received")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ShipmentEvent(BaseEvent):
    """Event for shipment operations."""

    user_id: str = Field(..., description="User ID for the shipment operation")
    shipment_event: ShipmentEventData = Field(..., description="Shipment event data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the event was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced")
    shipment_id: str = Field(..., description="Shipment ID")
    tracking_number: str = Field(..., description="Tracking number")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "shipments-service"


# Meeting Poll Events
class MeetingPollData(BaseModel):
    """Meeting poll data structure."""

    id: str = Field(..., description="Unique poll ID")
    meeting_id: str = Field(..., description="Meeting ID")
    poll_type: str = Field(
        ..., description="Poll type (single_choice, multiple_choice, etc.)"
    )
    question: str = Field(..., description="Poll question")
    options: List[str] = Field(..., description="Poll options")
    responses: List[Dict[str, Any]] = Field(
        default_factory=list, description="Poll responses"
    )
    total_responses: int = Field(default=0, description="Total number of responses")
    is_active: bool = Field(default=True, description="Whether the poll is active")
    is_anonymous: bool = Field(
        default=False, description="Whether responses are anonymous"
    )
    allow_multiple_votes: bool = Field(
        default=False, description="Whether multiple votes are allowed"
    )
    created_by: str = Field(..., description="User who created the poll")
    created_at: datetime = Field(..., description="When the poll was created")
    expires_at: Optional[datetime] = Field(None, description="When the poll expires")
    results_visible: bool = Field(
        default=True, description="Whether results are visible"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MeetingPollEvent(BaseEvent):
    """Event for meeting poll operations."""

    user_id: str = Field(..., description="User ID for the poll operation")
    poll: MeetingPollData = Field(..., description="Poll data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the poll was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced")
    meeting_id: str = Field(..., description="Meeting ID")
    poll_id: str = Field(..., description="Poll ID")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "meetings-service"


# Booking Events
class BookingData(BaseModel):
    """Booking data structure."""

    id: str = Field(..., description="Unique booking ID")
    resource_id: str = Field(..., description="Resource ID")
    resource_type: str = Field(..., description="Resource type (room, equipment, etc.)")
    resource_name: str = Field(..., description="Resource name")
    start_time: datetime = Field(..., description="Booking start time")
    end_time: datetime = Field(..., description="Booking end time")
    duration_minutes: int = Field(..., description="Duration in minutes")
    status: str = Field(..., description="Booking status")
    booking_type: str = Field(..., description="Type of booking")
    attendees: List[str] = Field(default_factory=list, description="Attendee emails")
    organizer: str = Field(..., description="Organizer email")
    purpose: str = Field(..., description="Booking purpose")
    notes: Optional[str] = Field(None, description="Additional notes")
    recurring_pattern: Optional[str] = Field(None, description="Recurring pattern")
    recurring_end_date: Optional[datetime] = Field(
        None, description="Recurring end date"
    )
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BookingEvent(BaseEvent):
    """Event for booking operations."""

    user_id: str = Field(..., description="User ID for the booking operation")
    booking: BookingData = Field(..., description="Booking data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the booking was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced")
    resource_id: str = Field(..., description="Resource ID")
    resource_type: str = Field(..., description="Resource type")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "meetings-service"
