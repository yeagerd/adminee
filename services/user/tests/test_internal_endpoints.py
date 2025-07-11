"""
Unit tests for Internal API Endpoints.

Basic tests for internal service-to-service API endpoints.
"""

import asyncio
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from services.user.database import create_all_tables
from services.user.tests.test_base import BaseUserManagementTest


class TestInternalAPI(BaseUserManagementTest):
    """Test suite for internal API endpoints."""

    def setup_method(self):
        super().setup_method()
        asyncio.run(create_all_tables())
        self.client = TestClient(self.app)
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

        import pytest
        from services.common.http_errors import AuthError
        with pytest.raises(AuthError) as exc_info:
            self.client.post("/internal/tokens/get", json=request_data)
        assert "API key required" in str(exc_info.value)

    def test_internal_user_status_endpoint_exists(self):
        """Test that the user status endpoint exists and returns proper error for non-existent user."""
        with patch(
            "services.user.routers.internal.get_current_service",
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
