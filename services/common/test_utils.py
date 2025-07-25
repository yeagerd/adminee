"""
Common test utilities for integration tests across all services.

Provides base classes with HTTP call detection rakes to prevent real external
HTTP calls during testing while allowing TestClient to work properly.
"""

import os
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class BaseIntegrationTest:
    """Base class for integration tests with HTTP call detection rakes."""

    def setup_method(self, method: object) -> None:
        """Set up test environment with HTTP call detection rakes."""
        # HTTP Call Detection Rakes - These will fail the test if real HTTP calls are made
        # We need to be selective to allow TestClient to work but catch real external calls

        self.http_patches = [
            # Patch both sync and async httpx clients
            patch(
                "httpx.AsyncClient._send_single_request",
                side_effect=AssertionError(
                    "Real HTTP call detected! AsyncClient._send_single_request was called"
                ),
            ),
            patch(
                "httpx.Client._send_single_request",
                side_effect=AssertionError(
                    "Real HTTP call detected! Client._send_single_request was called"
                ),
            ),
            # Also patch the sync client send method
            patch(
                "httpx.Client.send",
                side_effect=AssertionError(
                    "Real HTTP call detected! Client.send was called"
                ),
            ),
            # Patch requests
            patch(
                "requests.adapters.HTTPAdapter.send",
                side_effect=AssertionError(
                    "Real HTTP call detected! requests HTTPAdapter.send was called"
                ),
            ),
            # Patch urllib
            patch(
                "urllib.request.urlopen",
                side_effect=AssertionError(
                    "Real HTTP call detected! urllib.request.urlopen was called"
                ),
            ),
        ]

        # Start all HTTP detection patches
        for http_patch in self.http_patches:
            http_patch.start()

        # Use in-memory SQLite database instead of temporary files
        os.environ["DB_URL_OFFICE"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/1"

        # Mock Redis completely to avoid any connection attempts
        self.redis_patcher = patch("redis.Redis")
        self.mock_redis_class = self.redis_patcher.start()
        self.mock_redis_instance = MagicMock()
        self.mock_redis_class.return_value = self.mock_redis_instance

        # Configure Redis mock behavior
        self.mock_redis_instance.ping.return_value = True
        self.mock_redis_instance.get.return_value = None
        self.mock_redis_instance.set.return_value = True
        self.mock_redis_instance.delete.return_value = 1
        self.mock_redis_instance.exists.return_value = False

    def teardown_method(self, method: object) -> None:
        """Clean up after each test method."""
        # Stop all patches
        for http_patch in self.http_patches:
            http_patch.stop()
        self.redis_patcher.stop()

    def create_test_client(self, app: "FastAPI") -> TestClient:
        """Create a FastAPI test client for the given app."""
        return TestClient(app)


class BaseOfficeServiceIntegrationTest(BaseIntegrationTest):
    """Base class for Office Service integration tests."""

    def setup_method(self, method: object) -> None:
        """Set up Office Service specific test environment."""
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

        # Use in-memory SQLite database instead of temporary files
        os.environ["DB_URL_OFFICE"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/1"

        # Mock Redis completely to avoid any connection attempts
        self.redis_patcher = patch("redis.Redis")
        self.mock_redis_class = self.redis_patcher.start()
        self.mock_redis_instance = MagicMock()
        self.mock_redis_class.return_value = self.mock_redis_instance

        # Configure Redis mock behavior
        self.mock_redis_instance.ping.return_value = True
        self.mock_redis_instance.get.return_value = None
        self.mock_redis_instance.set.return_value = True
        self.mock_redis_instance.delete.return_value = 1
        self.mock_redis_instance.exists.return_value = False

        # Office Service specific Redis patching
        self.office_redis_patcher = patch(
            "services.office.core.cache_manager.redis.Redis"
        )
        self.office_mock_redis_class = self.office_redis_patcher.start()
        self.office_mock_redis_instance = MagicMock()
        self.office_mock_redis_class.return_value = self.office_mock_redis_instance

        # Configure Office Service Redis mock behavior
        self.office_mock_redis_instance.ping.return_value = True
        self.office_mock_redis_instance.get.return_value = None
        self.office_mock_redis_instance.set.return_value = True
        self.office_mock_redis_instance.delete.return_value = 1
        self.office_mock_redis_instance.exists.return_value = False

        # Import and create test client
        from services.office.app.main import app

        self.client = self.create_test_client(app)

        # Set up default auth headers for tests
        # Import settings here to avoid module-level dependency
        from services.office.core.settings import get_settings

        settings = get_settings()
        self.auth_headers = {
            "X-User-Id": "test-user@example.com",
            "Authorization": f"Bearer {settings.api_frontend_office_key}",
        }

    def teardown_method(self, method: object) -> None:
        """Clean up Office Service specific patches."""
        # Stop all patches
        for http_patch in self.http_patches:
            http_patch.stop()
        self.redis_patcher.stop()
        self.office_redis_patcher.stop()


# For services that don't need specific setup, they can use the selective HTTP patches
class BaseSelectiveHTTPIntegrationTest(BaseIntegrationTest):
    """Base class for integration tests that need to allow TestClient but block external HTTP calls."""

    def setup_method(self, method: object) -> None:
        """Set up test environment with selective HTTP call detection."""
        # HTTP Call Detection Rakes - These will fail the test if real HTTP calls are made
        # We need to be selective to allow TestClient to work but catch real external calls

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

        # Use in-memory SQLite database instead of temporary files
        os.environ["DB_URL_OFFICE"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/1"

        # Mock Redis completely to avoid any connection attempts
        self.redis_patcher = patch("redis.Redis")
        self.mock_redis_class = self.redis_patcher.start()
        self.mock_redis_instance = MagicMock()
        self.mock_redis_class.return_value = self.mock_redis_instance

        # Configure Redis mock behavior
        self.mock_redis_instance.ping.return_value = True
        self.mock_redis_instance.get.return_value = None
        self.mock_redis_instance.set.return_value = True
        self.mock_redis_instance.delete.return_value = 1
        self.mock_redis_instance.exists.return_value = False

    def teardown_method(self, method: object) -> None:
        """Clean up after each test method."""
        # Stop all patches
        for http_patch in self.http_patches:
            http_patch.stop()
        self.redis_patcher.stop()
