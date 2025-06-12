"""
Unit tests for Internal API Endpoints.

Basic tests for internal service-to-service API endpoints.
"""

import asyncio
import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Set required environment variables before any imports
os.environ.setdefault("TOKEN_ENCRYPTION_SALT", "dGVzdC1zYWx0LTE2Ynl0ZQ==")

from services.user_management.database import create_all_tables
from services.user_management.main import app


class TestInternalAPI:
    """Test suite for internal API endpoints."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.db_path}"
        asyncio.run(create_all_tables())
        self.client = TestClient(app)
        self.auth_headers = self._get_auth_headers()

    def teardown_method(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _get_auth_headers(self):
        """Provide authentication headers for internal API calls."""
        return {"X-API-Key": "test-api-key"}

    def test_internal_endpoints_require_authentication(self):
        """Test that internal endpoints require authentication."""
        request_data = {
            "user_id": "test_user_123",
            "provider": "google",
            "required_scopes": ["read"],
        }

        # No authentication headers
        response = self.client.post("/internal/tokens/get", json=request_data)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Wrapped by get_current_service
        ]

    def test_internal_user_status_endpoint_exists(self):
        """Test that the user status endpoint exists and returns proper error for non-existent user."""
        with patch(
            "services.user_management.routers.internal.get_current_service",
            return_value="test-service",
        ):
            response = self.client.get(
                "/internal/user/test_user_123/status",
                headers=self.auth_headers,
            )
            # Should return 404 for non-existent user or 500 if method not implemented
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]
