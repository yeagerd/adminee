"""
Email collision detection utilities for user management service.

Provides email normalization and collision detection using fast local rules
to handle provider-specific email formatting rules (Gmail dots, plus addressing, etc.).
"""

from typing import Any, Dict, Optional

from sqlalchemy import and_, select

from services.common.logging_config import get_logger
from services.user.database import get_async_session
from services.user.models.user import User

logger = get_logger(__name__)


class EmailCollisionDetector:
    """Detect and handle email collisions during user registration."""

    def __init__(self) -> None:
        """Initialize the email collision detector."""
        pass

    def _simple_email_normalize(self, email: str) -> str:
        """
        Fast email normalization using local provider-specific rules.

        Args:
            email: Email address to normalize

        Returns:
            str: Normalized email address
        """
        if not email:
            return email

        email = email.strip().lower()

        # Handle Gmail-style normalization (remove dots and plus addressing)
        if email.endswith("@gmail.com") or email.endswith("@googlemail.com"):
            local, domain = email.split("@")
            # Remove dots and plus addressing
            local = local.replace(".", "")
            if "+" in local:
                local = local.split("+")[0]
            return f"{local}@gmail.com"

        # Handle Yahoo-style normalization (remove dots and plus addressing)
        elif email.endswith("@yahoo.com"):
            local, domain = email.split("@")
            # Remove dots and plus addressing
            local = local.replace(".", "")
            if "+" in local:
                local = local.split("+")[0]
            return f"{local}@{domain}"

        # Handle Outlook/Hotmail plus addressing (only remove plus, keep dots)
        elif email.endswith("@outlook.com") or email.endswith("@hotmail.com"):
            local, domain = email.split("@")
            if "+" in local:
                local = local.split("+")[0]
            return f"{local}@{domain}"

        # Basic normalization for other domains
        return email

    def normalize_email(self, email: str) -> str:
        """
        Normalize an email address using fast local provider-specific rules.

        Args:
            email: Email address to normalize

        Returns:
            str: Normalized email address
        """
        if not email:
            return email

        try:
            return self._simple_email_normalize(email)
        except Exception as e:
            logger.warning(f"Failed to normalize email {email}: {e}")
            return email.strip().lower()

    async def normalize_email_async(self, email: str) -> str:
        """
        Async wrapper for normalize_email method.

        Args:
            email: Email address to normalize

        Returns:
            str: Normalized email address
        """
        return self.normalize_email(email)

    async def check_collision(self, email: str) -> Optional[User]:
        """
        Check if normalized email already exists.

        Args:
            email: Email address to check for collision

        Returns:
            Existing user if collision found, None otherwise
        """
        normalized_email = self.normalize_email(email)
        logger.debug(
            f"COLLISION: Checking for user with normalized_email={normalized_email}"
        )

        async_session = get_async_session()
        async with async_session() as session:
            stmt = select(User).where(
                and_(
                    User.normalized_email == normalized_email,  # type: ignore[arg-type]
                    User.deleted_at.is_(None),  # type: ignore[union-attr]
                )
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                logger.warning(
                    f"COLLISION: Found existing user={user.external_auth_id} for normalized_email={normalized_email}"
                )
            else:
                logger.debug(
                    f"COLLISION: No user found for normalized_email={normalized_email}"
                )
            return user

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
            normalized_email = self.normalize_email(email)
            logger.debug(
                f"COLLISION: get_collision_details for email={email}, normalized={normalized_email}"
            )

            collision_user = await self.check_collision(normalized_email)

            if collision_user:
                logger.warning(
                    f"COLLISION: Collision detected for normalized_email={normalized_email}, user={collision_user.external_auth_id}"
                )
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
                        "domain": self._get_email_domain(normalized_email),
                    },
                }
            else:
                logger.debug(
                    f"COLLISION: No collision for normalized_email={normalized_email}"
                )
                return {
                    "available": True,
                    "normalized_email": normalized_email,
                    "collision": False,
                    "reason": "available",
                    "email_info": {
                        "original": email,
                        "normalized": normalized_email,
                        "domain": self._get_email_domain(normalized_email),
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
        Get email information including fast local normalization.

        Args:
            email: Email address to analyze

        Returns:
            Dictionary with email information
        """
        try:
            normalized_email = self._simple_email_normalize(email)
            return {
                "original_email": email,
                "normalized_email": normalized_email,
                "mailbox_domain": self._get_email_domain(normalized_email),
                "mx_records": [],
                "is_valid": True,
            }
        except Exception as e:
            return {
                "original_email": email,
                "normalized_email": email.strip().lower(),
                "mailbox_domain": "unknown",
                "mx_records": [],
                "is_valid": False,
                "error": str(e),
            }

    def normalize_email_by_provider(self, email: str, provider: str) -> str:
        """
        Normalize email using known provider-specific rules.

        Alternative interface when provider is explicitly known.
        Performance is equivalent to auto-detection since both use local rules.

        Args:
            email: Email address to normalize
            provider: OAuth provider ('google', 'microsoft', 'yahoo', etc.)

        Returns:
            str: Normalized email address
        """
        if not email:
            return email

        email = email.strip().lower()

        if "@" not in email:
            return email

        local, domain = email.split("@", 1)

        # Provider-specific normalization rules
        if provider == "google" or provider == "gmail":
            # Gmail: Remove dots and plus addressing
            local = local.replace(".", "")
            if "+" in local:
                local = local.split("+")[0]
            # Normalize domain to gmail.com
            if domain in ["googlemail.com", "gmail.com"]:
                domain = "gmail.com"

        elif provider == "microsoft" or provider == "outlook":
            # Microsoft/Outlook: Remove plus addressing (keep dots)
            if "+" in local:
                local = local.split("+")[0]
            # Normalize common Microsoft domains
            if domain in ["hotmail.com", "outlook.com", "live.com", "msn.com"]:
                domain = "outlook.com"

        elif provider == "yahoo":
            # Yahoo: Remove dots and plus addressing
            local = local.replace(".", "")
            if "+" in local:
                local = local.split("+")[0]

        # For other providers, just basic normalization
        # (Could add more providers like Apple, etc.)

        return f"{local}@{domain}"

    def _get_email_domain(self, email: str) -> str:
        """
        Extract domain from email address.

        Args:
            email: Email address

        Returns:
            str: Email domain (e.g., 'gmail.com', 'company.com', etc.)
        """
        if not email or "@" not in email:
            return "unknown"

        domain = email.split("@")[1].lower()
        return domain


# Global instance for easy access
email_collision_detector = EmailCollisionDetector()
