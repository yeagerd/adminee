"""
Contact event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent


class ContactData(BaseModel):
    """Contact data structure."""

    id: str = Field(..., description="Unique contact ID")
    display_name: str = Field(..., description="Contact display name")
    given_name: Optional[str] = Field(None, description="Contact's given/first name")
    family_name: Optional[str] = Field(None, description="Contact's family/last name")
    email_addresses: List[str] = Field(
        default_factory=list, description="Email addresses"
    )
    phone_numbers: List[Dict[str, str]] = Field(
        default_factory=list, description="Phone numbers with types"
    )
    addresses: List[Dict[str, Any]] = Field(
        default_factory=list, description="Physical addresses"
    )
    organizations: List[Dict[str, str]] = Field(
        default_factory=list, description="Organizational information"
    )
    birthdays: List[datetime] = Field(
        default_factory=list, description="Birthday dates"
    )
    notes: Optional[str] = Field(None, description="Additional notes about the contact")
    provider: str = Field(..., description="Contact provider (google, outlook, etc.)")
    provider_contact_id: str = Field(..., description="Provider's internal contact ID")

    # Additional metadata
    photos: List[Dict[str, Any]] = Field(
        default_factory=list, description="Contact photos"
    )
    groups: List[str] = Field(default_factory=list, description="Contact groups")
    tags: List[str] = Field(default_factory=list, description="Contact tags")
    last_modified: Optional[datetime] = Field(
        None, description="Last modification time"
    )


class ContactEvent(BaseEvent):
    """Event for contact operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the contact operation")
    contact: ContactData = Field(..., description="Contact data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the contact was last updated")
    sync_timestamp: datetime = Field(
        ..., description="When the data was last synced from provider"
    )
    provider: str = Field(..., description="Contact provider (google, outlook, etc.)")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class ContactUpdateEvent(BaseEvent):
    """Event for individual contact updates (deprecated - use ContactEvent)."""

    user_id: str = Field(..., description="User ID for the contact update")
    contact: ContactData = Field(..., description="Updated contact data")
    update_type: str = Field(..., description="Type of update (create, update, delete)")
    change_reason: Optional[str] = Field(None, description="Reason for the change")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class ContactBatchEvent(BaseEvent):
    """Event for batch contact operations.

    Deprecated - use ContactEvent with batch_id instead.
    """

    user_id: str = Field(..., description="User ID for the batch operation")
    provider: str = Field(..., description="Contact provider")
    contacts: List[ContactData] = Field(
        ..., description="List of contacts in the batch"
    )
    operation: str = Field(..., description="Operation type (sync, import, export)")
    batch_id: str = Field(..., description="Unique batch identifier")

    # Progress tracking
    total_contacts: Optional[int] = Field(None, description="Total contacts to process")
    processed_count: int = Field(
        default=0, description="Number of contacts processed so far"
    )

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"
