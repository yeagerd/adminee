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

    Includes UI preferences, notifications, AI settings, integrations, and privacy.
    Each user has exactly one preferences record.
    """

    ormar_config = base_ormar_config.copy(tablename="user_preferences")

    id: int = ormar.Integer(primary_key=True)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")

    # UI Preferences
    theme: str = ormar.String(max_length=20, default="light")  # light, dark, auto
    language: str = ormar.String(max_length=10, default="en")  # ISO language codes
    timezone: str = ormar.String(max_length=50, default="UTC")  # IANA timezone
    date_format: str = ormar.String(max_length=20, default="MM/DD/YYYY")
    time_format: str = ormar.String(max_length=10, default="12h")  # 12h, 24h

    # Notification Preferences
    email_notifications: bool = ormar.Boolean(default=True)
    push_notifications: bool = ormar.Boolean(default=True)
    marketing_emails: bool = ormar.Boolean(default=False)

    # AI Preferences
    ai_suggestions_enabled: bool = ormar.Boolean(default=True)
    ai_model_preference: str = ormar.String(max_length=50, default="gpt-4")
    auto_summarization: bool = ormar.Boolean(default=True)

    # Integration Preferences
    google_integration_enabled: bool = ormar.Boolean(default=False)
    microsoft_integration_enabled: bool = ormar.Boolean(default=False)
    slack_integration_enabled: bool = ormar.Boolean(default=False)

    # Privacy Preferences
    data_retention_days: int = ormar.Integer(default=365)  # Days to keep data
    share_analytics: bool = ormar.Boolean(default=False)  # Share usage analytics

    # Timestamps
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
