"""
Base classes for Chat Service tests.

Provides common setup and teardown for all chat service tests,
including required environment variables and HTTP call prevention.
"""

import os

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseChatTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Chat Service tests with HTTP call prevention."""

    def setup_method(self):
        """Set up Chat Service test environment with required variables."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(None)

        # Set required environment variables for Chat Service
        os.environ["DB_URL_CHAT"] = "sqlite:///:memory:"
        os.environ["API_FRONTEND_CHAT_KEY"] = "test-frontend-chat-key"
        os.environ["API_CHAT_USER_KEY"] = "test-chat-user-key"
        os.environ["API_CHAT_OFFICE_KEY"] = "test-chat-office-key"

        # Optional environment variables with test defaults
        os.environ.setdefault("LOG_LEVEL", "INFO")
        os.environ.setdefault("LOG_FORMAT", "json")

    def teardown_method(self):
        """Clean up Chat Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(None)
