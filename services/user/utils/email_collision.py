"""
Email collision detection utilities for user management service.

Provides email normalization and collision detection using the email-normalize library
to handle provider-specific email formatting rules (Gmail dots, plus addressing, etc.).
"""

import logging
from typing import Any, Dict, Optional

from email_normalize import normalize
from sqlalchemy import select

from services.user.database import get_async_session
from services.user.models.user import User

logger = logging.getLogger(__name__)


class EmailCollisionDetector:
    """Detect and handle email collisions during user registration."""

    def __init__(self):
        """Initialize the email collision detector."""
        pass

    async def normalize_email(self, email: str) -> str:
        """
        Normalize an email address using provider-specific rules.

        Args:
            email: Email address to normalize

        Returns:
            str: Normalized email address
        """
        if not email:
            return email

        try:
            # Use the email-normalize library
            result = normalize(email)
            return result.normalized_address
        except Exception as e:
            # Fallback to basic normalization if email-normalize fails
            logger.warning(f"Failed to normalize email {email}: {e}")
            return email.strip().lower()

    async def check_collision(self, email: str) -> Optional[User]:
        """
        Check if normalized email already exists.

        Args:
            email: Email address to check for collision

        Returns:
            Existing user if collision found, None otherwise
        """
        normalized_email = await self.normalize_email(email)

        # Query for existing user with same normalized email
        async_session = get_async_session()
        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.normalized_email == normalized_email, User.deleted_at.is_(None)
                )
            )
            return result.scalar_one_or_none()

    async def get_collision_details(self, email: str) -> dict:
        """
        Get detailed information about email collision status.

        Args:
            email: Email address to check

        Returns:
            dict: Collision details including availability, normalized email, and collision info
        """
        if not email:
            return {
                "available": False,
                "normalized_email": "",
                "collision": False,
                "reason": "empty_email",
                "email_info": {},
            }

        try:
            # Normalize the email
            normalized_email = await self.normalize_email(email)

            # Check for collision
            collision_user = await self.check_collision(normalized_email)

            if collision_user:
                return {
                    "available": False,
                    "normalized_email": normalized_email,
                    "collision": True,
                    "existing_user_id": collision_user.external_auth_id,
                    "existing_user_email": collision_user.email,
                    "reason": "email_exists",
                    "email_info": {
                        "original": email,
                        "normalized": normalized_email,
                        "provider": self._get_email_provider(normalized_email),
                    },
                }
            else:
                return {
                    "available": True,
                    "normalized_email": normalized_email,
                    "collision": False,
                    "reason": "available",
                    "email_info": {
                        "original": email,
                        "normalized": normalized_email,
                        "provider": self._get_email_provider(normalized_email),
                    },
                }
        except Exception as e:
            logger.error(f"Error checking collision details for {email}: {e}")
            return {
                "available": False,
                "normalized_email": email.strip().lower(),
                "collision": False,
                "reason": "error",
                "error": str(e),
                "email_info": {},
            }

    async def get_email_info(self, email: str) -> Dict[str, Any]:
        """
        Get comprehensive email information including normalization.

        Args:
            email: Email address to analyze

        Returns:
            Dictionary with email information
        """
        try:
            result = normalize(email)
            return {
                "original_email": email,
                "normalized_email": result.normalized_address,
                "mailbox_provider": result.mailbox_provider,
                "mx_records": result.mx_records,
                "is_valid": True,
            }
        except Exception as e:
            return {
                "original_email": email,
                "normalized_email": email.strip().lower(),
                "mailbox_provider": "unknown",
                "mx_records": [],
                "is_valid": False,
                "error": str(e),
            }

    def _get_email_provider(self, email: str) -> str:
        """
        Extract email provider from email address.

        Args:
            email: Email address

        Returns:
            str: Email provider (e.g., 'gmail', 'outlook', etc.)
        """
        if not email or "@" not in email:
            return "unknown"

        domain = email.split("@")[1].lower()

        # Common providers
        if "gmail.com" in domain:
            return "gmail"
        elif "outlook.com" in domain or "hotmail.com" in domain:
            return "outlook"
        elif "yahoo.com" in domain:
            return "yahoo"
        elif "icloud.com" in domain or "me.com" in domain:
            return "icloud"
        else:
            return domain


# Global instance for easy access
email_collision_detector = EmailCollisionDetector()
