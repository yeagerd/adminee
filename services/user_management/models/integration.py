"""
Integration model for User Management Service.

Defines OAuth integration connections with external providers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import ormar
from pydantic import EmailStr

from ..database import base_ormar_config
from .user import User


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


class Integration(ormar.Model):
    """
    Integration model for OAuth connections to external providers.

    Stores connection status, provider information, and metadata.
    Links to encrypted tokens for secure credential storage.
    """

    ormar_config = base_ormar_config.copy(tablename="integrations")

    id: int = ormar.Integer(primary_key=True)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")

    # Provider information
    provider: IntegrationProvider = ormar.Enum(enum_class=IntegrationProvider)
    status: IntegrationStatus = ormar.Enum(
        enum_class=IntegrationStatus, default=IntegrationStatus.PENDING
    )

    # Provider-specific user information
    provider_user_id: Optional[str] = ormar.String(max_length=255, nullable=True)
    provider_email: Optional[EmailStr] = ormar.String(max_length=255, nullable=True)

    # OAuth scopes and metadata
    scopes: Optional[Dict[str, Any]] = ormar.JSON(nullable=True)
    metadata: Optional[Dict[str, Any]] = ormar.JSON(
        nullable=True
    )  # Provider-specific data

    # Sync information
    last_sync_at: Optional[datetime] = ormar.DateTime(nullable=True)
    error_message: Optional[str] = ormar.Text(nullable=True)

    # Timestamps
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
