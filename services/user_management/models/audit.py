"""
Audit log model for User Management Service.

Provides comprehensive audit logging for compliance and security tracking.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import ormar

from ..database import base_ormar_config
from .user import User


class AuditLog(ormar.Model):
    """
    Audit log model for tracking all user actions and system events.

    Provides comprehensive logging for compliance, security, and debugging.
    Stores structured data about user actions, API calls, and system changes.
    """

    ormar_config = base_ormar_config.copy(tablename="audit_logs")

    id: int = ormar.Integer(primary_key=True)
    user: Optional[User] = ormar.ForeignKey(User, nullable=True, ondelete="SET NULL")

    # Action details
    action: str = ormar.String(max_length=100)  # create, update, delete, login, etc.
    resource_type: str = ormar.String(max_length=50)  # user, integration, token, etc.
    resource_id: Optional[str] = ormar.String(max_length=255, nullable=True)

    # Additional context
    details: Optional[Dict[str, Any]] = ormar.JSON(nullable=True)  # Structured details

    # Request metadata
    ip_address: Optional[str] = ormar.String(max_length=45, nullable=True)  # IPv4/IPv6
    user_agent: Optional[str] = ormar.String(max_length=500, nullable=True)

    # Timestamp
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
