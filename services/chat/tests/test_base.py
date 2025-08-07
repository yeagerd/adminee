"""
Base classes for Chat Service tests.

Provides common setup and teardown for all chat service tests,
including required settings and HTTP call prevention.
"""

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseChatTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Chat Service tests with HTTP call prevention."""

    def setup_method(self, method: object) -> None:
        """Set up Chat Service test environment with required settings."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(method)

        # Import chat settings module
        import services.chat.settings as chat_settings

        # Store original settings singleton for cleanup
        self._original_settings = chat_settings._settings

        # Create test settings instance
        from services.chat.settings import Settings

        test_settings = Settings(
            db_url_chat="sqlite:///:memory:",
            api_frontend_chat_key="test-frontend-chat-key",
            api_chat_user_key="test-chat-user-key",
            api_chat_office_key="test-chat-office-key",
            user_service_url="http://localhost:8001",
            office_service_url="http://localhost:8003",
            log_level="INFO",
            log_format="json",
            pagination_secret_key="test-pagination-secret-key",
        )

        # Set the test settings as the singleton
        chat_settings._settings = test_settings

        # Initialize database schema for testing
        import asyncio

        from services.chat.history_manager import create_all_tables_for_testing

        try:
            asyncio.run(create_all_tables_for_testing())
        except RuntimeError:
            # If we're already in an event loop, create a task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, create_all_tables_for_testing())
                future.result()

    def teardown_method(self, method: object) -> None:
        """Clean up Chat Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(method)

        # Restore original settings singleton
        import services.chat.settings as chat_settings

        chat_settings._settings = self._original_settings
