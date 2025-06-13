"""
Encrypted token model for User Management Service.

Stores encrypted OAuth tokens with secure user-specific encryption.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Text, func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from services.user_management.models.integration import Integration

if TYPE_CHECKING:
    from services.user_management.models.integration import Integration
    from services.user_management.models.user import User


class TokenType(str, Enum):
    """Types of OAuth tokens stored."""

    ACCESS = "access"
    REFRESH = "refresh"


class EncryptedToken(SQLModel, table=True):
    """
    Encrypted token model for secure OAuth token storage.

    Stores access and refresh tokens using user-specific encryption keys.
    Linked to specific integrations and users for proper access control.
    """

    __tablename__ = "encrypted_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    integration_id: int = Field(foreign_key="integrations.id", ondelete="CASCADE")

    # Token information
    token_type: TokenType = Field(
        sa_column=Column(SQLEnum(TokenType), name="token_type")
    )
    encrypted_value: str = Field(
        sa_column=Column(Text)
    )  # Base64 encoded encrypted token

    # Token metadata
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    scopes: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

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
    user: Optional["User"] = Relationship(back_populates="tokens")
    integration: Optional["Integration"] = Relationship(back_populates="tokens")
