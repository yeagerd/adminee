"""
Base event models for PubSub messages with distributed tracing support.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    """Metadata for all events including distributed tracing."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event ID"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    source_service: str = Field(..., description="Service that published the event")
    source_version: str = Field(
        default="1.0.0", description="Version of the source service"
    )

    # Distributed tracing fields
    trace_id: Optional[str] = Field(None, description="OpenTelemetry trace ID")
    span_id: Optional[str] = Field(None, description="OpenTelemetry span ID")
    parent_span_id: Optional[str] = Field(
        None, description="Parent span ID for nested operations"
    )

    # Request context
    request_id: Optional[str] = Field(
        None, description="Request ID that triggered this event"
    )
    user_id: Optional[str] = Field(
        None, description="User ID associated with this event"
    )

    # Additional context
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for related events"
    )
    tags: Dict[str, Any] = Field(
        default_factory=dict, description="Additional tags for the event"
    )


class BaseEvent(BaseModel):
    """Base class for all PubSub events."""

    metadata: EventMetadata = Field(..., description="Event metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def add_trace_context(
        self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None
    ) -> None:
        """Add distributed tracing context to the event."""
        self.metadata.trace_id = trace_id
        self.metadata.span_id = span_id
        self.metadata.parent_span_id = parent_span_id

    def add_request_context(
        self, request_id: str, user_id: Optional[str] = None
    ) -> None:
        """Add request context to the event."""
        self.metadata.request_id = request_id
        self.metadata.user_id = user_id

    def add_correlation_id(self, correlation_id: str) -> None:
        """Add correlation ID for related events."""
        self.metadata.correlation_id = correlation_id

    def add_tags(self, **tags: Any) -> None:
        """Add tags to the event."""
        self.metadata.tags.update(tags)
