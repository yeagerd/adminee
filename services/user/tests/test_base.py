"""
Base classes for User Management tests.

Provides common setup and teardown for all user management tests,
including required environment variables and database setup.
"""

import os
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient


class BaseUserManagementTest:
    """Base class for all User Management tests (unit and integration)."""

    def setup_method(self):
        """Set up User Management test environment with required variables."""
        # Create temporary database file for tests that need file-based SQLite
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Set required environment variables for User Management service
        os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.db_path}"
        os.environ["TOKEN_ENCRYPTION_SALT"] = "dGVzdC1zYWx0LTE2Ynl0ZQ=="
        os.environ["API_FRONTEND_USER_KEY"] = "test-api-key"

        # Optional environment variables with test defaults
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
        os.environ.setdefault("ENVIRONMENT", "test")

        # Import app after environment variables are set
        from services.user.main import app

        self.app = app

    def teardown_method(self):
        """Clean up User Management test environment."""
        # Close and remove temporary database file
        if hasattr(self, "db_fd"):
            os.close(self.db_fd)
        if hasattr(self, "db_path") and os.path.exists(self.db_path):
            os.unlink(self.db_path)


class BaseUserManagementIntegrationTest(BaseUserManagementTest):
    """Base class for User Management integration tests with full app setup."""

    def setup_method(self):
        """Set up User Management integration test environment."""
        # Call parent setup for environment variables
        super().setup_method()

        # Use selective HTTP patches that don't interfere with TestClient
        self.http_patches = [
            # Patch async httpx client (most likely to be used for real external calls)
            patch(
                "httpx.AsyncClient._send_single_request",
                side_effect=AssertionError(
                    "Real HTTP call detected! AsyncClient._send_single_request was called"
                ),
            ),
            # Patch requests (commonly used for external calls)
            patch(
                "requests.adapters.HTTPAdapter.send",
                side_effect=AssertionError(
                    "Real HTTP call detected! requests HTTPAdapter.send was called"
                ),
            ),
            # Patch urllib (basic HTTP library)
            patch(
                "urllib.request.urlopen",
                side_effect=AssertionError(
                    "Real HTTP call detected! urllib.request.urlopen was called"
                ),
            ),
            # Note: We don't patch httpx.Client.send because TestClient uses it internally
        ]

        # Start all HTTP detection patches
        for http_patch in self.http_patches:
            http_patch.start()

        # Reload the database module to pick up the new environment variable
        import importlib

        import services.user.database

        importlib.reload(services.user.database)

        # Actually create the database tables
        import asyncio

        from services.user.database import create_all_tables

        asyncio.run(create_all_tables())

        # Create test client using app from base class
        self.client = TestClient(self.app)

        # Set up authentication overrides
        self._override_auth()

    def teardown_method(self):
        """Clean up User Management integration test environment."""
        # Stop all patches
        if hasattr(self, "http_patches"):
            for http_patch in self.http_patches:
                http_patch.stop()

        # Clear app overrides
        if hasattr(self, "app"):
            self.app.dependency_overrides.clear()
        if hasattr(self, "_patcher"):
            self._patcher.stop()

        # Call parent teardown
        super().teardown_method()

    def _override_auth(self):
        """Override authentication for testing."""
        from unittest.mock import AsyncMock

        from services.user.auth.nextauth import get_current_user  # Changed here

        async def mock_get_current_user():
            return "user_123"

        # This async def function can still be used as a side_effect if needed,
        # but we'll create an AsyncMock instance directly for the patch.
        # async def mock_verify_user_ownership_side_effect(
        #     current_user_id: str, resource_user_id: str
        # ):
        #     return None

        mock_verify_ownership_instance = AsyncMock(return_value=None)

        self.app.dependency_overrides[get_current_user] = mock_get_current_user
        patcher = patch(
            "services.user.auth.nextauth.verify_user_ownership",  # Changed here
            new=mock_verify_ownership_instance,
        )
        self._patcher = patcher.start()
