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

        response = self.client.post("/v1/internal/tokens/get", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "API key required" in data["message"]

    def test_internal_user_status_endpoint_exists(self):
        """Test that the user status endpoint exists and returns proper error for non-existent user."""

        from fastapi.testclient import TestClient

        from services.user.main import app

        with patch("services.user.settings.get_settings") as mock_settings:
            from services.user.settings import Settings

            test_settings = Settings(db_url_user_management="sqlite:///:memory:")
            test_settings.api_frontend_user_key = "test-frontend-key"
            test_settings.api_chat_user_key = "test-chat-key"
            test_settings.api_office_user_key = "test-office-key"
            mock_settings.return_value = test_settings
            client = TestClient(app)
            response = client.get(
                "/v1/internal/users/nonexistent-user/status",
                headers={"X-API-Key": "test-api-key"},
            )
            assert response.status_code in (404, 422, 400, 403)
