"""
Contact database models for the Contacts Service.

Adapted from services/common/models/email_contact.py to use SQLModel
for database persistence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EmailContactEventCount(SQLModel, table=False):
    """Count of events for a specific contact and event type."""

    event_type: str = Field(
        ..., description="Type of event (email, calendar, document)"
    )
    count: int = Field(default=0, description="Number of events of this type")
    last_seen: datetime = Field(
        ..., description="When this contact was last seen in this event type"
    )
    first_seen: datetime = Field(
        ..., description="When this contact was first seen in this event type"
    )


class Contact(SQLModel, table=True):
    """Contact database model with event type counters and last_seen tracking."""

    __tablename__ = "contacts"  # type: ignore[assignment]

    id: Optional[str] = Field(
        default=None, primary_key=True, description="Unique contact ID"
    )
    user_id: str = Field(..., description="User ID who owns this contact")
    email_address: str = Field(..., description="Contact's email address")
    display_name: Optional[str] = Field(
        default=None, description="Contact's display name"
    )
    given_name: Optional[str] = Field(
        default=None, description="Contact's given/first name"
    )
    family_name: Optional[str] = Field(
        default=None, description="Contact's family/last name"
    )

    # Event tracking - stored as JSONB in PostgreSQL
    event_counts: Dict[str, EmailContactEventCount] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Count of events by type for this contact",
    )
    total_event_count: int = Field(
        default=0, description="Total number of events across all types"
    )
    last_seen: datetime = Field(
        ..., description="When this contact was last seen in any event"
    )
    first_seen: datetime = Field(..., description="When this contact was first seen")

    # Contact relevance scoring
    relevance_score: float = Field(
        default=0.0, description="Contact relevance score (0.0 to 1.0)"
    )
    relevance_factors: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Factors contributing to relevance score",
    )

    # Metadata
    source_services: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Services where this contact was discovered",
    )
    tags: List[str] = Field(
        default_factory=list, sa_column=Column(JSON), description="Contact tags"
    )
    notes: Optional[str] = Field(
        default=None, description="Additional notes about the contact"
    )
    
    # Office Service integration fields
    provider: Optional[str] = Field(
        default=None, description="Office service provider (Google, Microsoft, etc.)"
    )
    last_synced: Optional[datetime] = Field(
        default=None, description="When this contact was last synced from Office Service"
    )
    phone_numbers: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON), description="Contact phone numbers"
    )
    addresses: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, sa_column=Column(JSON), description="Contact addresses"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this contact record was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this contact record was last updated",
    )

    def add_event(self, event_type: str, event_timestamp: datetime) -> None:
        """Add an event for this contact."""
        now = datetime.now(timezone.utc)

        # Update or create event count
        if event_type not in self.event_counts:
            self.event_counts[event_type] = EmailContactEventCount(
                event_type=event_type,
                count=0,
                last_seen=event_timestamp,
                first_seen=event_timestamp,
            )

        # Update event count
        event_count = self.event_counts[event_type]
        event_count.count += 1
        event_count.last_seen = event_timestamp

        # Update total counts
        self.total_event_count += 1
        self.last_seen = max(self.last_seen, event_timestamp)

        # Update timestamps
        self.updated_at = now

    def calculate_relevance_score(self) -> float:
        """Calculate contact relevance score based on various factors."""
        score = 0.0

        # Factor 1: Recency (0-30 points)
        days_since_last_seen = (datetime.now(timezone.utc) - self.last_seen).days
        recency_score = max(0, 30 - days_since_last_seen)
        score += recency_score

        # Factor 2: Event frequency (0-30 points)
        # More events = higher score, but with diminishing returns
        frequency_score = min(30, self.total_event_count * 2)
        score += frequency_score

        # Factor 3: Event diversity (0-20 points)
        # Contacts appearing in multiple event types get higher scores
        diversity_score = min(20, len(self.event_counts) * 5)
        score += diversity_score

        # Factor 4: Name completeness (0-20 points)
        name_score = 0
        if self.display_name:
            name_score += 10
        if self.given_name:
            name_score += 5
        if self.family_name:
            name_score += 5
        score += name_score

        # Normalize to 0.0-1.0 range
        normalized_score = min(1.0, score / 100.0)

        # Store relevance factors for debugging
        self.relevance_factors = {
            "recency": recency_score / 100.0,
            "frequency": frequency_score / 100.0,
            "diversity": diversity_score / 100.0,
            "name_completeness": name_score / 100.0,
            "total_score": normalized_score,
        }

        self.relevance_score = normalized_score
        return normalized_score

    def get_primary_name(self) -> str:
        """Get the primary display name for this contact."""
        if self.display_name:
            return self.display_name

        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        elif self.family_name:
            return self.family_name

        return self.email_address

    def to_vespa_document(self) -> Dict[str, Any]:
        """Convert to Vespa document format."""
        return {
            "doc_id": f"contact_{self.user_id}_{self.email_address}",
            "user_id": self.user_id,
            "content_type": "contact",
            "title": self.get_primary_name(),
            "content": self.notes or "",
            "search_text": f"{self.get_primary_name()} {self.email_address}",
            "created_at": int(self.created_at.timestamp()),
            "updated_at": int(self.updated_at.timestamp()),
            "last_updated": int(self.last_seen.timestamp()),
            "sync_timestamp": int(self.updated_at.timestamp()),
            "operation": "create",
            "batch_id": None,
            "tags": self.tags,
            "metadata": {
                "email_address": self.email_address,
                "given_name": self.given_name,
                "family_name": self.family_name,
                "event_counts": {
                    k: v.model_dump() for k, v in self.event_counts.items()
                },
                "total_event_count": self.total_event_count,
                "relevance_score": self.relevance_score,
                "relevance_factors": self.relevance_factors,
                "source_services": self.source_services,
            },
        }
