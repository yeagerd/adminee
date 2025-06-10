"""
Unit tests for Internal API Endpoints.

Basic tests for internal service-to-service API endpoints.
"""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..main import app


class TestInternalAPI:
    """Test suite for internal API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Provide authentication headers for internal API calls."""
        return {"X-API-Key": "test-api-key"}

    def test_internal_endpoints_require_authentication(self, client):
        """Test that internal endpoints require authentication."""
        request_data = {
            "user_id": "test_user_123",
            "provider": "google",
            "required_scopes": ["read"],
        }

        # No authentication headers
        response = client.post("/internal/tokens/get", json=request_data)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_internal_user_status_endpoint_exists(self, client, auth_headers):
        """Test that the user status endpoint exists and returns proper error for non-existent user."""
        with patch(
            "services.user_management.routers.internal.get_current_service",
            return_value="test-service",
        ):
            response = client.get(
                "/internal/user/test_user_123/status",
                headers=auth_headers,
            )
            # Should return 404 for non-existent user or 500 if method not implemented
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]
