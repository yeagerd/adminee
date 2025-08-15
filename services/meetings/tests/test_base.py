"""
Base classes for Meetings Service tests.

Provides common setup and teardown for all meetings service tests,
including required environment variables and database setup.
"""

import os
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseMeetingsTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Meetings Service tests with HTTP call prevention."""

    def setup_method(self, method):
        """Set up Meetings Service test environment with required variables."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(method)

        # Use a unique temp file for each test
        self._db_fd, self._db_path = tempfile.mkstemp(suffix=".sqlite3")
        db_url = f"sqlite:///{self._db_path}"

        # Set environment variable for database URL
        os.environ["DB_URL_MEETINGS"] = db_url

        # Enable test mode for rate limiting
        from services.meetings.services.security import set_test_mode

        set_test_mode(True)

        # Import meetings settings module
        import services.meetings.settings as meetings_settings

        # Store original settings singleton for cleanup
        self._original_settings = meetings_settings._settings

        # Create test settings instance
        from services.meetings.settings import Settings

        test_settings = Settings(
            db_url_meetings=db_url,
            api_email_sync_meetings_key="test-email-sync-key",
            api_meetings_office_key="test-meetings-office-key",
            api_meetings_user_key="test-meetings-user-key",
            api_frontend_meetings_key="test-frontend-meetings-key",
            office_service_url="http://localhost:8003",
            user_service_url="http://localhost:8001",
            log_level="INFO",
            log_format="json",
            pagination_secret_key="test-pagination-secret-key",
        )

        # Set the test settings as the singleton
        meetings_settings._settings = test_settings

        # Initialize database schema for testing
        import asyncio

        from services.meetings.models import create_all_tables_for_testing

        try:
            asyncio.run(create_all_tables_for_testing())
        except RuntimeError:
            # If we're already in an event loop, create a task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, create_all_tables_for_testing())
                future.result()

        # Import app after environment variables are set
        from services.meetings.main import app

        self.app = app

    def teardown_method(self, method):
        """Clean up Meetings Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(method)

        # Restore original settings singleton
        import services.meetings.settings as meetings_settings

        meetings_settings._settings = self._original_settings

        # Close and remove temporary database file
        if hasattr(self, "_db_fd"):
            os.close(self._db_fd)
        if hasattr(self, "_db_path") and os.path.exists(self._db_path):
            os.unlink(self._db_path)


class BaseMeetingsIntegrationTest(BaseMeetingsTest):
    """Base class for Meetings Service integration tests with full app setup."""

    def setup_method(self, method):
        """Set up Meetings Service integration test environment."""
        # Call parent setup for environment variables and database
        super().setup_method(method)

        # Create test client using app from base class
        self.client = TestClient(self.app)

        # Set up authentication overrides if needed
        self._override_auth()

    def _override_auth(self):
        """Override authentication for testing."""
        # Override authentication dependencies if needed for testing
        # This can be customized based on specific test requirements
        pass
