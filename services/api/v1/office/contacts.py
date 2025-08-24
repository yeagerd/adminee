"""
Office service contacts schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from .email import EmailAddress
from .models import Provider


class ContactPhone(BaseModel):
    type: Optional[str] = Field(
        None, description="Type of phone number (work, mobile, home)"
    )
    number: str = Field(..., description="Phone number in E.164 or localized format")


class Contact(BaseModel):
    id: str
    full_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    emails: List[EmailAddress] = []
    primary_email: Optional[EmailAddress] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    phones: List[ContactPhone] = []
    photo_url: Optional[str] = None
    # Provenance Information
    provider: Provider
    provider_contact_id: str
    account_email: EmailStr
    account_name: Optional[str] = None


class ContactList(BaseModel):
    """Response model for contact lists."""

    success: bool
    data: Optional[List[Contact]] = None  # ✅ Contains contacts, metadata, etc.
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class ContactCreateResponse(BaseModel):
    """Response model for contact creation."""

    success: bool
    contact: Optional[Contact] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str


class ContactUpdateResponse(BaseModel):
    """Response model for contact updates."""

    success: bool
    contact: Optional[Contact] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str


class ContactDeleteResponse(BaseModel):
    """Response model for contact deletion."""

    success: bool
    deleted_contact_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str
