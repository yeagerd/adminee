"""
User preferences model for User Management Service.

Defines comprehensive user preference settings across all categories.
"""

from datetime import datetime, timezone

import ormar

from ..database import base_ormar_config
from .user import User


class UserPreferences(ormar.Model):
    """
    User preferences model for storing all user settings.

    Uses JSON fields to store structured preference data by category.
    Each user has exactly one preferences record.
    """

    ormar_config = base_ormar_config.copy(tablename="user_preferences")

    id: int = ormar.Integer(primary_key=True)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")

    # Version field for migration support
    version: str = ormar.String(max_length=10, default="1.0")

    # Structured preference data stored as JSON
    ui_preferences: dict = ormar.JSON(default={})
    notification_preferences: dict = ormar.JSON(default={})
    ai_preferences: dict = ormar.JSON(default={})
    integration_preferences: dict = ormar.JSON(default={})
    privacy_preferences: dict = ormar.JSON(default={})

    # Timestamps
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
