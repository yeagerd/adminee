"""
Base classes for Meetings Service tests.

Provides common setup and teardown for all meetings service tests,
including required environment variables and database setup.
"""

import os
import tempfile

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseMeetingsTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Meetings Service tests with HTTP call prevention."""

    def setup_method(self):
        """Set up Meetings Service test environment with required variables."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(None)

        # Create temporary database file for tests that need file-based SQLite
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Set required environment variables for Meetings Service
        os.environ["DB_URL_MEETINGS"] = f"sqlite:///{self.db_path}"
        os.environ["API_EMAIL_SYNC_MEETINGS_KEY"] = "test-email-sync-key"
        os.environ["API_MEETINGS_OFFICE_KEY"] = "test-meetings-office-key"
        os.environ["API_MEETINGS_USER_KEY"] = "test-meetings-user-key"
        os.environ["API_FRONTEND_MEETINGS_KEY"] = "test-frontend-meetings-key"

        # Optional environment variables with test defaults
        os.environ.setdefault("OFFICE_SERVICE_URL", "http://localhost:8003")
        os.environ.setdefault("USER_SERVICE_URL", "http://localhost:8001")
        os.environ.setdefault("LOG_LEVEL", "INFO")
        os.environ.setdefault("LOG_FORMAT", "json")

    def teardown_method(self):
        """Clean up Meetings Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(None)

        # Close and remove temporary database file
        if hasattr(self, "db_fd"):
            os.close(self.db_fd)
        if hasattr(self, "db_path") and os.path.exists(self.db_path):
            os.unlink(self.db_path)
