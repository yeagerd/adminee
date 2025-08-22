"""
Email event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent


class EmailData(BaseModel):
    """Email data structure."""

    id: str = Field(..., description="Unique email ID")
    thread_id: str = Field(..., description="Email thread ID")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    from_address: str = Field(..., description="Sender email address")
    to_addresses: List[str] = Field(..., description="Recipient email addresses")
    cc_addresses: List[str] = Field(
        default_factory=list, description="CC email addresses"
    )
    bcc_addresses: List[str] = Field(
        default_factory=list, description="BCC email addresses"
    )
    received_date: datetime = Field(..., description="When the email was received")
    sent_date: Optional[datetime] = Field(None, description="When the email was sent")
    labels: List[str] = Field(default_factory=list, description="Email labels/tags")
    is_read: bool = Field(default=False, description="Whether the email has been read")
    is_starred: bool = Field(default=False, description="Whether the email is starred")
    has_attachments: bool = Field(
        default=False, description="Whether the email has attachments"
    )
    provider: str = Field(..., description="Email provider (gmail, outlook, etc.)")
    provider_message_id: str = Field(..., description="Provider's internal message ID")

    # Additional metadata
    size_bytes: Optional[int] = Field(None, description="Email size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type of the email")
    headers: Dict[str, str] = Field(default_factory=dict, description="Email headers")


class EmailEvent(BaseEvent):
    """Event for email operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the email operation")
    email: EmailData = Field(..., description="Email data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(None, description="Batch identifier for batch operations")
    last_updated: datetime = Field(..., description="When the email was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced from provider")
    provider: str = Field(..., description="Email provider (gmail, outlook, etc.)")
    sync_type: str = Field(default="sync", description="Type of sync operation")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


# Keep EmailBackfillEvent for backward compatibility during transition
class EmailBackfillEvent(BaseEvent):
    """Event for email backfill operations (deprecated - use EmailEvent)."""

    user_id: str = Field(..., description="User ID for the backfill operation")
    provider: str = Field(..., description="Email provider being backfilled")
    emails: List[EmailData] = Field(..., description="List of emails to backfill")
    batch_size: int = Field(..., description="Number of emails in this batch")
    sync_type: str = Field(default="backfill", description="Type of sync operation")
    start_date: Optional[datetime] = Field(
        None, description="Start date for backfill range"
    )
    end_date: Optional[datetime] = Field(
        None, description="End date for backfill range"
    )
    folder: Optional[str] = Field(None, description="Email folder being processed")

    # Progress tracking
    total_emails: Optional[int] = Field(None, description="Total emails to process")
    processed_count: int = Field(
        default=0, description="Number of emails processed so far"
    )

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class EmailUpdateEvent(BaseEvent):
    """Event for individual email updates (deprecated - use EmailEvent)."""

    user_id: str = Field(..., description="User ID for the email update")
    email: EmailData = Field(..., description="Updated email data")
    update_type: str = Field(..., description="Type of update (create, update, delete)")
    change_reason: Optional[str] = Field(None, description="Reason for the change")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class EmailBatchEvent(BaseEvent):
    """Event for batch email operations (deprecated - use EmailEvent with batch_id)."""

    user_id: str = Field(..., description="User ID for the batch operation")
    provider: str = Field(..., description="Email provider")
    emails: List[EmailData] = Field(..., description="List of emails in the batch")
    operation: str = Field(..., description="Operation type (sync, import, export)")
    batch_id: str = Field(..., description="Unique batch identifier")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"
