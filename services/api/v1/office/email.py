"""
Office service email schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from services.api.v1.office.models import Provider


# Unified Email Models
class EmailAddress(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    name: Optional[str] = Field(None, max_length=100, description="Display name")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate that name is not empty if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty string to None
        return v.strip() if v else v


class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    body_text_unquoted: Optional[str] = (
        None  # Visible text content only (non-quoted part)
    )
    body_html_unquoted: Optional[str] = (
        None  # Visible HTML content only (non-quoted part)
    )
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = []
    cc_addresses: List[EmailAddress] = []
    bcc_addresses: List[EmailAddress] = []
    date: datetime
    labels: List[str] = []
    is_read: bool = False
    has_attachments: bool = False
    # Provenance Information
    provider: Provider
    provider_message_id: str
    account_email: EmailStr  # Which account this message belongs to
    account_name: Optional[str] = None  # Display name for the account


class EmailThread(BaseModel):
    id: str
    subject: Optional[str] = None
    messages: List[EmailMessage]
    participant_count: int
    last_message_date: datetime
    is_read: bool = False
    providers: List[Provider]


class Conversation(BaseModel):
    """Microsoft Graph conversation/thread model."""

    id: str = Field(..., description="Microsoft Graph conversation ID")
    topic: Optional[str] = Field(None, description="Conversation topic/subject")
    has_attachments: bool = Field(
        False, description="Whether conversation has attachments"
    )
    last_delivered_date_time: Optional[datetime] = Field(
        None, description="Last delivered message time"
    )
    unique_senders: List[str] = Field(
        default_factory=list, description="Unique sender email addresses"
    )
    preview: Optional[str] = Field(None, description="Preview of the conversation")


class EmailThreadListData(BaseModel):
    """Data structure for email thread list responses."""

    threads: List[EmailThread]
    total_count: int
    providers_used: List[str]
    provider_errors: Optional[Dict[str, str]] = None
    has_more: bool = False
    request_metadata: Dict[str, Any]


class EmailThreadList(BaseModel):
    """Response model for email thread lists."""

    success: bool
    data: Optional[EmailThreadListData] = None  # ✅ Contains threads and metadata
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class SendEmailRequest(BaseModel):
    """Request model for sending emails."""

    to: List[EmailAddress]
    subject: str
    body: str
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    reply_to_message_id: Optional[str] = None
    provider: Optional[str] = None  # If not specified, uses user's default preference
    importance: Optional[str] = None  # "high", "normal", "low"


class EmailSendResult(BaseModel):
    """Result data for email send operations."""

    message_id: str
    thread_id: Optional[str] = None
    provider: Provider
    sent_at: datetime
    recipient_count: int
    has_attachments: bool = False


class SendEmailResponse(BaseModel):
    """Response model for sending emails."""

    success: bool
    data: Optional[EmailSendResult] = None  # ✅ Specific response type
    error: Optional[Dict[str, Any]] = None
    request_id: str


class EmailDraftCreateRequest(BaseModel):
    """Request model for creating email drafts in providers (Google/Microsoft)."""

    # Action describes how the draft is created relative to an existing message
    action: str = Field(
        default="new",
        description="Draft action: new, reply, reply_all, forward",
    )
    to: Optional[List[EmailAddress]] = None
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    subject: Optional[str] = None
    body: Optional[str] = None

    # For threading: unified thread_id like gmail_xxx or outlook_xxx
    thread_id: Optional[str] = None
    # To create a reply/forward on providers that require message reference
    reply_to_message_id: Optional[str] = None

    # Explicit provider override; otherwise inferred from thread/message context
    provider: Optional[str] = None


class EmailDraftUpdateRequest(BaseModel):
    """Request model for updating email drafts in providers."""

    to: Optional[List[EmailAddress]] = None
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    provider: Optional[str] = None


class EmailDraftResult(BaseModel):
    """Result data for email draft operations."""

    draft_id: str
    thread_id: Optional[str] = None
    provider: Provider
    created_at: datetime
    updated_at: Optional[datetime] = None
    action: str  # new, reply, reply_all, forward


class EmailDraftResponse(BaseModel):
    """Response model for email draft operations."""

    success: bool
    data: Optional[EmailDraftResult] = None  # ✅ Specific response type
    error: Optional[Dict[str, Any]] = None
    request_id: str


class EmailMessageListData(BaseModel):
    """Data structure for email message list responses."""

    messages: List[EmailMessage]
    total_count: int
    providers_used: List[str]
    provider_errors: Optional[Dict[str, str]] = None
    has_more: bool = False
    request_metadata: Dict[str, Any]


class EmailMessageList(BaseModel):
    """Response model for email message lists."""

    success: bool
    data: Optional[EmailMessageListData] = None  # ✅ Contains messages and metadata
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class EmailFolder(BaseModel):
    """Model for email folders/labels."""

    label: str = Field(..., description="Unique identifier for the folder/label")
    name: str = Field(..., description="Display name for the folder/label")
    provider: Provider = Field(..., description="Provider this folder belongs to")
    provider_folder_id: Optional[str] = Field(
        None, description="Provider-specific folder ID"
    )
    account_email: EmailStr = Field(
        ..., description="Which account this folder belongs to"
    )
    account_name: Optional[str] = Field(
        None, description="Display name for the account"
    )
    is_system: bool = Field(
        False, description="Whether this is a system folder (inbox, sent, etc.)"
    )
    message_count: Optional[int] = Field(
        None, description="Number of messages in this folder"
    )


class EmailFolderListData(BaseModel):
    """Data structure for email folder list responses."""

    folders: List[EmailFolder]
    providers_used: List[str]
    provider_errors: Optional[Dict[str, str]] = None
    request_metadata: Dict[str, Any]


class EmailFolderList(BaseModel):
    """Response model for email folder lists."""

    success: bool
    data: Optional[EmailFolderListData] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class ApiError(BaseModel):
    """Error model for API responses."""

    type: str  # "validation_error", "auth_error", "provider_error", etc.
    message: str
    details: Optional[Dict[str, Any]] = None
    provider: Optional[Provider] = None
    retry_after: Optional[int] = None  # seconds
    request_id: str
