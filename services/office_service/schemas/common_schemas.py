from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union, TypeVar, Generic
from datetime import datetime
from enum import Enum

class Provider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class EmailAddress(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = Field(default_factory=list)
    cc_addresses: List[EmailAddress] = Field(default_factory=list)
    bcc_addresses: List[EmailAddress] = Field(default_factory=list)
    date: datetime
    labels: List[str] = Field(default_factory=list)
    is_read: bool = False
    has_attachments: bool = False
    provider: Provider
    provider_message_id: str
    account_email: EmailStr # Placeholder: In reality, this should be the specific account's email
    account_name: Optional[str] = None

class CalendarEvent(BaseModel):
    id: str
    calendar_id: str # Placeholder: This should be the unified ID of the calendar
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    attendees: List[EmailAddress] = Field(default_factory=list)
    organizer: Optional[EmailAddress] = None
    status: str = "confirmed"
    visibility: str = "default"
    provider: Provider
    provider_event_id: str
    account_email: EmailStr # Placeholder
    account_name: Optional[str] = None
    calendar_name: str # Placeholder
    created_at: datetime
    updated_at: datetime

class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: datetime
    modified_time: datetime
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None
    thumbnail_link: Optional[str] = None
    parent_folder_id: Optional[str] = None
    is_folder: bool = False
    provider: Provider
    provider_file_id: str
    account_email: EmailStr # Placeholder
    account_name: Optional[str] = None

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: Optional[int] = None
    next_page_token: Optional[str] = None
    has_more: bool = False
