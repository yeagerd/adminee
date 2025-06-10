"""
User model for User Management Service.

Defines the main User model with profile information and onboarding status.
"""

from datetime import datetime, timezone
from typing import Optional

import ormar
from pydantic import EmailStr

from ..database import base_ormar_config


class User(ormar.Model):
    """
    User model representing registered users in the system.

    Stores basic profile information and onboarding status.
    Connected to Clerk for authentication.
    """

    ormar_config = base_ormar_config.copy(tablename="users")

    id: str = ormar.String(primary_key=True, max_length=255)
    email: EmailStr = ormar.String(max_length=255, unique=True)
    first_name: Optional[str] = ormar.String(max_length=100, nullable=True)
    last_name: Optional[str] = ormar.String(max_length=100, nullable=True)
    profile_image_url: Optional[str] = ormar.String(max_length=500, nullable=True)
    onboarding_completed: bool = ormar.Boolean(default=False)
    onboarding_step: Optional[str] = ormar.String(max_length=50, nullable=True)
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = ormar.DateTime(nullable=True, default=None)
