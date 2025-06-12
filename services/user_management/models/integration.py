"""
Integration model for User Management Service.

Defines OAuth integration connections with external providers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import EmailStr
from sqlalchemy import JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Text, func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from services.user_management.models.user import User
    from services.user_management.models.token import EncryptedToken


class IntegrationProvider(str, Enum):
    """Supported OAuth integration providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    SLACK = "slack"


class IntegrationStatus(str, Enum):
    """Integration connection status."""

    ACTIVE = "active"  # Connected and working
    INACTIVE = "inactive"  # Disconnected by user
    ERROR = "error"  # Connection error or expired tokens
    PENDING = "pending"  # OAuth flow in progress


class Integration(SQLModel, table=True):
    """
    Integration model for OAuth connections to external providers.

    Stores connection status, provider information, and metadata.
    Links to encrypted tokens for secure credential storage.
    """

    __tablename__ = "integrations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")

    # Provider information
    provider: IntegrationProvider = Field(
        sa_column=Column(SQLEnum(IntegrationProvider), name="provider")
    )
    status: IntegrationStatus = Field(
        default=IntegrationStatus.PENDING,
        sa_column=Column(SQLEnum(IntegrationStatus), name="status"),
    )

    # Provider-specific user information
    provider_user_id: Optional[str] = Field(default=None, max_length=255)
    provider_email: Optional[EmailStr] = Field(default=None, max_length=255)

    # OAuth scopes and metadata
    scopes: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    provider_metadata: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )  # Provider-specific data

    # Sync information
    last_sync_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        ),
    )

    # Relationships
    user: Optional["User"] = Relationship(back_populates="integrations")
    tokens: list["EncryptedToken"] = Relationship(back_populates="integration")
