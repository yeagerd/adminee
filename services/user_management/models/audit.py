"""
Audit log model for User Management Service.

Provides comprehensive audit logging for compliance and security tracking.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from .user import User


class AuditLog(SQLModel, table=True):
    """
    Audit log model for tracking all user actions and system events.

    Provides comprehensive logging for compliance, security, and debugging.
    Stores structured data about user actions, API calls, and system changes.
    """

    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )

    # Action details
    action: str = Field(max_length=100)  # create, update, delete, login, etc.
    resource_type: str = Field(max_length=50)  # user, integration, token, etc.
    resource_id: Optional[str] = Field(default=None, max_length=255)

    # Additional context
    details: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )  # Structured details

    # Request metadata
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv4/IPv6
    user_agent: Optional[str] = Field(default=None, max_length=500)

    # Timestamp
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationship
    user: Optional["User"] = Relationship(back_populates="audit_logs")
