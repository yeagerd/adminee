"""
Encrypted token model for User Management Service.

Stores encrypted OAuth tokens with secure user-specific encryption.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import ormar

from ..database import base_ormar_config
from .integration import Integration
from .user import User


class TokenType(str, Enum):
    """Types of OAuth tokens stored."""

    ACCESS = "access"
    REFRESH = "refresh"


class EncryptedToken(ormar.Model):
    """
    Encrypted token model for secure OAuth token storage.

    Stores access and refresh tokens using user-specific encryption keys.
    Linked to specific integrations and users for proper access control.
    """

    ormar_config = base_ormar_config.copy(tablename="encrypted_tokens")

    id: int = ormar.Integer(primary_key=True)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")
    integration: Integration = ormar.ForeignKey(Integration, ondelete="CASCADE")

    # Token information
    token_type: TokenType = ormar.Enum(enum_class=TokenType)
    encrypted_value: str = ormar.Text()  # Base64 encoded encrypted token

    # Token metadata
    expires_at: Optional[datetime] = ormar.DateTime(nullable=True)
    scopes: Optional[Dict[str, Any]] = ormar.JSON(nullable=True)

    # Timestamps
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
