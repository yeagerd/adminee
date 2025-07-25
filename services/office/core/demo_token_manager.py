"""
Demo Token Manager for development and testing.

Provides a mock token manager that uses environment variables instead of
the User Management Service for easier development and testing workflows.
"""

import logging
import os
from typing import Any, Optional

from services.office.core.token_manager import TokenData, TokenManager

logger = logging.getLogger(__name__)


class DemoTokenManager(TokenManager):
    """
    Demo implementation of TokenManager that reads tokens from environment variables.

    This bypasses the user management service and uses predefined tokens for all users.
    Perfect for demos, development, and testing.
    """

    async def get_user_token(
        self, user_id: str, provider: str, scopes: list[str]
    ) -> Optional[TokenData]:
        """
        Get user token from environment variables instead of user service.

        Args:
            user_id: User identifier (ignored in demo mode)
            provider: Provider string (google or microsoft)
            scopes: List of required scopes (ignored in demo mode)

        Returns:
            TokenData if token is available in environment, None otherwise
        """
        logger.info(f"Demo mode: Getting token for user {user_id}, provider {provider}")

        # Map provider to environment variable
        env_var_map = {
            "google": "DEMO_GOOGLE_TOKEN",
            "microsoft": "DEMO_MICROSOFT_TOKEN",
        }

        env_var = env_var_map.get(provider)
        if not env_var:
            logger.warning(f"Unknown provider: {provider}")
            return None

        # Get token from environment
        token = os.getenv(env_var)
        if not token:
            logger.info(f"No demo token found for {provider} (env var: {env_var})")
            return None

        logger.info(f"Found demo token for {provider}")

        # Create TokenData object
        return TokenData(
            access_token=token,
            refresh_token=None,  # Not needed for demo
            expires_at=None,  # Assume tokens don't expire in demo
            provider=provider,
            user_id=user_id,
            scopes=scopes,
        )

    async def __aenter__(self) -> "DemoTokenManager":
        """Async context manager entry - no HTTP client needed for demo."""
        logger.debug("Demo TokenManager initialized")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - no cleanup needed for demo."""
        logger.debug("Demo TokenManager closed")
