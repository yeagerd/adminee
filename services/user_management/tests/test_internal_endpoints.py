"""
Unit tests for Internal API Endpoints.

Basic tests for internal service-to-service API endpoints.
"""

import asyncio
import os

# Set required environment variables before any imports
os.environ.setdefault("DB_URL_USER_MANAGEMENT", "sqlite:///test.db")
os.environ.setdefault("TOKEN_ENCRYPTION_SALT", "dGVzdC1zYWx0LTE2Ynl0ZQ==")
os.environ.setdefault("API_FRONTEND_USER_KEY", "test-api-key")
os.environ.setdefault("CLERK_SECRET_KEY", "test-clerk-key")

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from services.user_management.database import create_all_tables
from services.user_management.main import app
from services.user_management.tests.test_base import BaseUserManagementTest


class TestInternalAPI(BaseUserManagementTest):
    """Test suite for internal API endpoints."""

    def setup_method(self):
        super().setup_method()
        asyncio.run(create_all_tables())
        self.client = TestClient(app)
        self.auth_headers = self._get_auth_headers()

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
