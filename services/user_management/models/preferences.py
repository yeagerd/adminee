"""
User preferences model for User Management Service.

Defines comprehensive user preference settings across all categories.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, TYPE_CHECKING

from sqlalchemy import JSON, func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from services.user_management.models.user import User


class UserPreferences(SQLModel, table=True):
    """
    User preferences model for storing all user settings.

    Uses JSON fields to store structured preference data by category.
    Each user has exactly one preferences record.
    """

    __tablename__ = "user_preferences"

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
