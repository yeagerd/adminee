"""
Unit tests for integration management endpoints.

Tests the new /me/integrations endpoints that are used by the frontend.
The old user-specific APIs have been deprecated and removed.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import status

from services.user.models.integration import (
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.schemas.integration import (
    IntegrationListResponse,
    OAuthCallbackResponse,
    TokenRefreshResponse,
)
from services.user.tests.test_base import BaseUserManagementIntegrationTest


class TestMeIntegrationEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for /me/integrations endpoints."""

    def test_get_current_user_integrations_success(self):
        """Test successful retrieval of current user integrations."""
        mock_response = IntegrationListResponse(
            integrations=[],
            total=0,
            active_count=0,
            error_count=0,
        )

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integrations = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                "/v1/users/me/integrations",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["active_count"] == 0

    def test_get_current_user_integrations_with_filters(self):
        """Test current user integrations with filters."""
        mock_response = IntegrationListResponse(
            integrations=[],
            total=0,
            active_count=0,
            error_count=0,
        )

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integrations = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                "/v1/users/me/integrations",
                params={
                    "provider": "google",
                    "status": "active",
                    "include_token_info": "false",
                },
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        mock_service.return_value.get_user_integrations.assert_called_once_with(
            user_id="user_123",  # Updated to match actual user ID format
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            include_token_info=False,
        )

    def test_disconnect_current_user_integration_success(self):
        """Test successful disconnection of current user integration."""
        provider = "google"

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": IntegrationProvider.GOOGLE,
            "tokens_revoked": True,
            "data_deleted": False,
            "disconnected_at": datetime.now(timezone.utc),
            "error": None,
        }

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.disconnect_integration = AsyncMock(
                return_value=mock_response
            )
            response = self.client.delete(
                f"/v1/users/me/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["integration_id"] == 123
        assert data["provider"] == "google"

    def test_refresh_current_user_integration_tokens_success(self):
        """Test successful token refresh for current user integration."""
        provider = "google"

        mock_response = TokenRefreshResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            token_expires_at=datetime.now(timezone.utc),
            refreshed_at=datetime.now(timezone.utc),
            error=None,
        )

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.refresh_integration_tokens = AsyncMock(
                return_value=mock_response
            )
            response = self.client.put(
                f"/v1/users/me/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["integration_id"] == 123
        assert data["provider"] == "google"

    def test_get_current_user_specific_integration_success(self):
        """Test successful retrieval of specific integration for current user."""
        provider = "google"

        mock_response = {
            "id": 123,
            "user_id": "user_123",  # Updated to match actual user ID format
            "provider": "google",
            "status": "active",
            "scopes": ["email", "profile"],
            "external_user_id": "google_user_123",
            "external_email": "user@example.com",
            "external_name": "Test User",
            "has_access_token": True,
            "has_refresh_token": True,
            "token_expires_at": datetime.now(timezone.utc).isoformat(),
            "token_created_at": datetime.now(timezone.utc).isoformat(),
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "last_error": None,
            "error_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integration = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/me/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 123
        assert data["provider"] == "google"
        assert data["status"] == "active"

    def test_check_current_user_integration_health_success(self):
        """Test successful health check for current user integration."""
        provider = "google"

        mock_response = {
            "integration_id": 123,
            "provider": IntegrationProvider.GOOGLE,
            "status": IntegrationStatus.ACTIVE,
            "healthy": True,
            "last_check_at": datetime.now(timezone.utc),
            "issues": [],
            "recommendations": [],
        }

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.check_integration_health = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/me/integrations/{provider}/health",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["integration_id"] == 123
        assert data["provider"] == "google"
        assert data["healthy"] is True

    def test_get_provider_scopes_success(self):
        """Test successful retrieval of provider scopes."""
        provider = "google"

        mock_response = {
            "provider": "google",
            "scopes": [
                {
                    "name": "email",
                    "description": "Access to email address",
                    "required": True,
                    "sensitive": False,
                },
                {
                    "name": "profile",
                    "description": "Access to profile information",
                    "required": False,
                    "sensitive": False,
                },
            ],
        }

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_provider_scopes = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/me/integrations/{provider}/scopes",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "google"
        assert len(data["scopes"]) == 2

    def test_start_current_user_oauth_flow_success(self):
        """Test successful OAuth flow initiation for current user."""
        request_data = {
            "provider": "google",
            "redirect_uri": "https://app.example.com/oauth/callback",
            "scopes": ["email", "profile"],
        }

        mock_response = {
            "authorization_url": "https://accounts.google.com/oauth/authorize?state=abc123",
            "state": "abc123",
            "provider": "google",
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "requested_scopes": ["email", "profile"],
        }

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.start_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/v1/users/me/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorization_url"] == mock_response["authorization_url"]
        assert data["state"] == mock_response["state"]
        assert data["provider"] == mock_response["provider"]

    def test_complete_current_user_oauth_flow_success(self):
        """Test successful OAuth flow completion for current user."""
        mock_response = OAuthCallbackResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            scopes=["https://www.googleapis.com/auth/calendar"],
            external_user_info={"email": "test@example.com", "name": "Test User"},
            error=None,
        )

        with patch(
            "services.user.services.integration_service.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/v1/users/me/integrations/oauth/callback?provider=google",
                json={
                    "code": "authorization_code_123",
                    "state": "state_123",
                },
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["integration_id"] == 123
        assert data["provider"] == "google"
        assert data["status"] == "active"


class TestMeIntegrationEndpointSecurity(BaseUserManagementIntegrationTest):
    """Test cases for /me/integrations endpoint security."""

    def test_me_endpoints_require_authentication(self):
        """Test that all /me/integrations endpoints require authentication."""
        provider = "google"

        # Clear any auth overrides to test unauthenticated access
        self.app.dependency_overrides.clear()

        # Test various /me endpoints without authentication
        endpoints = [
            "/v1/users/me/integrations",
            "/v1/users/me/integrations/oauth/start",
            f"/v1/users/me/integrations/{provider}",
            f"/v1/users/me/integrations/{provider}/refresh",
            f"/v1/users/me/integrations/{provider}/health",
            f"/v1/users/me/integrations/{provider}/scopes",
        ]

        for endpoint in endpoints:
            if "start" in endpoint:
                response = self.client.post(endpoint, json={})
            elif "refresh" in endpoint:
                response = self.client.put(endpoint, json={})
            elif "oauth/callback" in endpoint:
                response = self.client.post(endpoint, json={})
            else:
                response = self.client.get(endpoint)

            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ], f"Endpoint {endpoint} should require authentication"
