"""
Webhook event schemas for User Management Service.

Defines Pydantic models for validating incoming webhook payloads
from external services like Clerk.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ClerkWebhookEventData(BaseModel):
    """Base class for Clerk webhook event data."""

    id: str = Field(..., description="Unique identifier for the user")
    email_addresses: Optional[List[Dict[str, Any]]] = Field(
        None, description="Array of email addresses"
    )
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    image_url: Optional[str] = Field(None, description="User's profile image URL")
    created_at: Optional[int] = Field(
        None, description="Creation timestamp in milliseconds"
    )
    updated_at: Optional[int] = Field(
        None, description="Update timestamp in milliseconds"
    )

    @property
    def primary_email(self) -> Optional[str]:
        """Get the primary email address."""
        if (
            self.email_addresses
            and isinstance(self.email_addresses, list)
            and len(self.email_addresses) > 0
        ):
            for email_obj in self.email_addresses:
                if isinstance(email_obj, dict) and email_obj.get("email_address"):
                    return email_obj["email_address"]
        return None


class ClerkWebhookEvent(BaseModel):
    """Clerk webhook event payload structure."""

    type: str = Field(..., description="Event type (e.g., user.created, user.updated)")
    data: ClerkWebhookEventData = Field(..., description="Event data payload")
    object: str = Field(..., description="Object type (e.g., event)")
    timestamp: Optional[int] = Field(None, description="Event timestamp")

    @field_validator("type")
    def validate_event_type(cls, v):
        """Validate that we support this event type."""
        supported_events = ["user.created", "user.updated", "user.deleted"]
        if v not in supported_events:
            raise ValueError(
                f"Unsupported event type: {v}. Supported: {supported_events}"
            )
        return v


class WebhookResponse(BaseModel):
    """Standard webhook response model."""

    success: bool = Field(
        ..., description="Whether the webhook was processed successfully"
    )
    message: str = Field(..., description="Response message")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Processing timestamp",
    )
    event_id: Optional[str] = Field(None, description="ID of the processed event")
