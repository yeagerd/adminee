"""
User preferences model for User Management Service.

Defines comprehensive user preference settings across all categories.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from sqlalchemy import JSON, func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from services.user.models.user import User


class UserPreferences(SQLModel, table=True):
    """
    User preferences model for storing all user settings.

    Uses JSON fields to store structured preference data by category.
    Each user has exactly one preferences record.
    """

    __tablename__ = "user_preferences"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")

    # Version field for migration support
    version: str = Field(default="1.0", max_length=10)

    # Structured preference data stored as JSON
    ui_preferences: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    notification_preferences: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    ai_preferences: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    integration_preferences: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    privacy_preferences: Dict = Field(default_factory=dict, sa_column=Column(JSON))

    # User timezone preference (IANA timezone string) [DEPRECATED: use timezone_mode/manual_timezone]
    timezone: str = Field(default="UTC", max_length=50)  # DEPRECATED

    # Timezone mode: "auto" (browser) or "manual" (user override)
    timezone_mode: str = Field(
        default="auto", max_length=10, description="Timezone mode: 'auto' or 'manual'"
    )
    manual_timezone: str = Field(
        default="",
        max_length=50,
        description="Manual timezone override (IANA name, or empty if not set)",
    )

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

    # Relationship
    user: Optional["User"] = Relationship(back_populates="preferences")
