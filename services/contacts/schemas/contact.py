"""
Contact schemas for API requests and responses.

Moved from services/common/models/email_contact.py and adapted for the Contacts Service.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EmailContactUpdate(BaseModel):
    """Update model for email contacts."""

    display_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailContactSearchResult(BaseModel):
    """Search result for email contacts."""

    from services.contacts.models.contact import Contact
    
    contact: Contact
    relevance_score: float
    match_highlights: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ContactCreate(BaseModel):
    """Create model for contacts."""

    user_id: str = Field(..., description="User ID who owns this contact")
    email_address: str = Field(..., description="Contact's email address")
    display_name: Optional[str] = Field(None, description="Contact's display name")
    given_name: Optional[str] = Field(None, description="Contact's given/first name")
    family_name: Optional[str] = Field(None, description="Contact's family/last name")
    tags: Optional[List[str]] = Field(default_factory=list, description="Contact tags")
    notes: Optional[str] = Field(None, description="Additional notes about the contact")


class ContactResponse(BaseModel):
    """Response model for contacts."""

    from services.contacts.models.contact import Contact
    
    contact: Contact
    success: bool = True
    message: Optional[str] = None


class ContactListResponse(BaseModel):
    """Response model for contact lists."""

    from services.contacts.models.contact import Contact
    
    contacts: List[Contact]
    total: int
    limit: int
    offset: int
    success: bool = True
    message: Optional[str] = None


class ContactSearchRequest(BaseModel):
    """Request model for contact search."""

    query: Optional[str] = Field(None, description="Search query for name or email")
    user_id: str = Field(..., description="User ID to search contacts for")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    source_services: Optional[List[str]] = Field(None, description="Filter by source services")


class ContactStatsResponse(BaseModel):
    """Response model for contact statistics."""

    total_contacts: int
    total_events: int
    by_service: dict
    success: bool = True
    message: Optional[str] = None
