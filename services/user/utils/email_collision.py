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

    async def normalize_email(self, email: str) -> str:
        """
        Normalize email using email-normalize library.
        
        Args:
            email: Email address to normalize
            
        Returns:
            Normalized email address
            
        Raises:
            ValueError: If email is invalid or normalization fails
        """
        if not email or not email.strip():
            raise ValueError("Email address cannot be empty")
        
        try:
            result = normalize(email)
            return result.normalized_address
        except Exception as e:
            logger.warning(f"Failed to normalize email {email}: {e}")
            # Fallback to basic normalization
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
        # Note: normalized_email field doesn't exist yet in Phase 1
        # For now, we'll check against the regular email field
        async_session = get_async_session()
        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.email == normalized_email,
                    User.deleted_at.is_(None)
                )
            )
            return result.scalar_one_or_none()

    async def get_collision_details(self, email: str) -> Dict[str, Any]:
        """
        Get detailed information about email collision.
        
        Args:
            email: Email address to check for collision
            
        Returns:
            Dictionary with collision details
        """
        existing_user = await self.check_collision(email)
        
        if not existing_user:
            return {"collision": False}
        
        # Get normalization info
        try:
            result = normalize(email)
            provider_info = {
                "mailbox_provider": result.mailbox_provider,
                "mx_records": result.mx_records,
            }
        except Exception:
            provider_info = {}
        
        return {
            "collision": True,
            "existing_user_id": existing_user.id,
            "original_email": existing_user.email,
            "normalized_email": getattr(existing_user, 'normalized_email', None),
            "created_at": existing_user.created_at.isoformat() if existing_user.created_at else None,
            "auth_provider": existing_user.auth_provider,
            "provider_info": provider_info,
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


# Global instance for easy access
email_collision_detector = EmailCollisionDetector() 