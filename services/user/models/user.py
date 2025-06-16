"""
User model for User Management Service.

Defines the main User model with profile information and onboarding status.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from pydantic import EmailStr
from sqlalchemy import func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from services.user.models.audit import AuditLog
from services.user.models.integration import Integration
from services.user.models.preferences import UserPreferences
from services.user.models.token import EncryptedToken

if TYPE_CHECKING:
    from services.user.models.audit import AuditLog
    from services.user.models.integration import Integration
    from services.user.models.preferences import UserPreferences
    from services.user.models.token import EncryptedToken


class User(SQLModel, table=True):
    """
    User model representing registered users in the system.

    Stores basic profile information and onboarding status.
    Uses internal database ID as primary key with external auth ID for authentication providers.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    external_auth_id: str = Field(unique=True, index=True, max_length=255)
    auth_provider: str = Field(default="clerk", max_length=50)
    email: EmailStr = Field(unique=True, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    profile_image_url: Optional[str] = Field(default=None, max_length=500)
    onboarding_completed: bool = Field(default=False)
    onboarding_step: Optional[str] = Field(default=None, max_length=50)
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
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Relationships (using string literals to avoid circular imports)
    preferences: Optional["UserPreferences"] = Relationship(back_populates="user")
    integrations: list["Integration"] = Relationship(back_populates="user")
    tokens: list["EncryptedToken"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")
