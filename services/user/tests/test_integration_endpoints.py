"""
Unit tests for integration management endpoints.

Tests OAuth flow management, integration status, token operations,
health monitoring, and provider configuration endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import status

from services.common.http_errors import NotFoundError, ServiceError
from services.user.models.integration import (
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.schemas.integration import (
    IntegrationListResponse,
)
from services.user.tests.test_base import BaseUserManagementIntegrationTest


class TestIntegrationListEndpoint(BaseUserManagementIntegrationTest):
    """Test cases for listing user integrations."""

    def test_list_integrations_success(self):
        user_id = "user_123"
        mock_response = {
            "integrations": [
                {
                    "id": 1,
                    "user_id": "user_123",
                    "provider": "google",
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "scopes": ["email", "profile"],
                    "external_user_info": {"email": "user@example.com"},
                    "token_expires_at": datetime.now(timezone.utc).isoformat(),
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": None,
                    "has_access_token": True,
                    "has_refresh_token": True,
                }
            ],
            "total": 1,
            "active_count": 1,
            "error_count": 0,
        }
        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integrations = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/{user_id}/integrations/",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["active_count"] == 1
        assert len(data["integrations"]) == 1
        assert data["integrations"][0]["provider"] == "google"

    def test_list_integrations_with_filters(self):
        user_id = "user_123"
        mock_response = IntegrationListResponse(
            integrations=[],
            total=0,
            active_count=0,
            error_count=0,
        )
        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integrations = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/{user_id}/integrations/",
                params={
                    "provider": "google",
                    "status": "active",
                    "include_token_info": "false",
                },
            )
        assert response.status_code == status.HTTP_200_OK
        mock_service.return_value.get_user_integrations.assert_called_once_with(
            user_id=user_id,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            include_token_info=False,
        )

    def test_list_integrations_unauthorized(self):
        user_id = "user_123"
        # Clear any auth overrides to test unauthorized access
        self.app.dependency_overrides.clear()
        response = self.client.get(f"/v1/users/{user_id}/integrations/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_integrations_user_not_found(self):
        user_id = "user_123"
        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_user_integrations.side_effect = NotFoundError(
                "User not found"
            )
            response = self.client.get(
                f"/v1/users/{user_id}/integrations/",
                headers={"Authorization": "Bearer valid-token"},
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "User not found" in data["message"]


class TestOAuthFlowEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for OAuth flow management."""

    def test_start_oauth_flow_success(self):
        """Test successful OAuth flow initiation."""
        user_id = "user_123"

        request_data = {
            "provider": "google",
            "redirect_uri": "https://app.example.com/oauth/callback",
            "scopes": ["email", "profile"],
            "state_data": {"return_url": "/dashboard"},
        }

        mock_response = {
            "authorization_url": "https://accounts.google.com/oauth/authorize?state=abc123",
            "state": "abc123",
            "provider": "google",
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "requested_scopes": ["email", "profile"],
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.start_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                f"/v1/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorization_url"] == mock_response["authorization_url"]
        assert data["state"] == mock_response["state"]
        assert data["provider"] == mock_response["provider"]

    def test_start_oauth_flow_microsoft_success(self):
        """Test successful OAuth flow initiation for Microsoft."""
        user_id = "user_123"

        request_data = {
            "provider": "microsoft",
            "redirect_uri": "https://app.example.com/oauth/callback",
            "scopes": ["User.Read", "Calendars.Read"],
        }

        mock_response = {
            "authorization_url": "https://login.microsoftonline.com/oauth/authorize?state=def456",
            "state": "def456",
            "provider": "microsoft",
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "requested_scopes": ["User.Read", "Calendars.Read"],
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.start_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                f"/v1/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorization_url"] == mock_response["authorization_url"]
        assert data["state"] == mock_response["state"]
        assert data["provider"] == mock_response["provider"]

    def test_start_oauth_flow_invalid_provider(self):
        """Test OAuth flow initiation with invalid provider."""
        user_id = "user_123"
        request_data = {
            "provider": "invalid_provider",
            "redirect_uri": "https://app.example.com/oauth/callback",
        }

        response = self.client.post(
            f"/v1/users/{user_id}/integrations/oauth/start",
            json=request_data,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_complete_oauth_flow_success(self):
        """Test successful OAuth flow completion."""
        request_data = {
            "code": "authorization_code_123",
            "state": "state_123",
        }

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": "google",
            "status": "active",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "external_user_info": {"email": "test@example.com", "name": "Test User"},
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/v1/users/user_123/integrations/oauth/callback?provider=google",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == mock_response["success"]
        assert data["integration_id"] == mock_response["integration_id"]
        assert data["provider"] == mock_response["provider"]
        assert data["status"] == mock_response["status"]

    def test_complete_oauth_flow_microsoft_success(self):
        """Test successful OAuth flow completion for Microsoft."""
        request_data = {
            "code": "authorization_code_456",
            "state": "state_456",
        }

        mock_response = {
            "success": True,
            "integration_id": 456,
            "provider": "microsoft",
            "status": "active",
            "scopes": ["https://graph.microsoft.com/Calendars.ReadWrite"],
            "external_user_info": {"email": "test@example.com", "name": "Test User"},
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/v1/users/user_123/integrations/oauth/callback?provider=microsoft",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == mock_response["success"]
        assert data["integration_id"] == mock_response["integration_id"]
        assert data["provider"] == mock_response["provider"]
        assert data["status"] == mock_response["status"]

    @patch("services.user.services.audit_service.audit_logger.log_audit_event")
    def test_complete_oauth_flow_with_error(self, mock_audit):
        """Test OAuth flow completion with error."""
        request_data = {
            "code": "invalid_code",
            "state": "state_123",
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow.side_effect = ServiceError(
                message="Invalid authorization code"
            )
            response = self.client.post(
                "/v1/users/user_123/integrations/oauth/callback?provider=google",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid authorization code" in data["message"]

    def test_complete_oauth_flow_service_error(self):
        """Test OAuth flow completion with service error."""
        request_data = {
            "code": "authorization_code_123",
            "state": "state_123",
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow.side_effect = Exception(
                "Service error"
            )
            response = self.client.post(
                "/v1/users/user_123/integrations/oauth/callback?provider=google",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestIntegrationManagementEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for integration management."""

    def test_disconnect_integration_success(self):
        """Test successful integration disconnection."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.disconnect_integration = AsyncMock()
            response = self.client.delete(
                f"/v1/users/{user_id}/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        mock_service.return_value.disconnect_integration.assert_called_once_with(
            user_id=user_id, provider=provider
        )

    def test_disconnect_integration_not_found(self):
        """Test integration disconnection when integration not found."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.disconnect_integration.side_effect = (
                NotFoundError("Integration not found")
            )
            response = self.client.delete(
                f"/v1/users/{user_id}/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Integration not found" in data["message"]

    def test_refresh_integration_tokens_success(self):
        """Test successful token refresh."""
        user_id = "user_123"
        provider = "google"

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": "google",
            "token_expires_at": datetime.now(timezone.utc),
            "refreshed_at": datetime.now(timezone.utc),
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.refresh_integration_tokens = AsyncMock(
                return_value=mock_response
            )
            response = self.client.put(
                f"/v1/users/{user_id}/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == mock_response["success"]
        assert data["integration_id"] == mock_response["integration_id"]
        assert data["provider"] == mock_response["provider"]

    def test_refresh_integration_tokens_failure(self):
        """Test token refresh failure."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.refresh_integration_tokens.side_effect = (
                ServiceError(message="Token refresh failed")
            )
            response = self.client.put(
                f"/v1/users/{user_id}/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Token refresh failed" in data["message"]

    def test_check_integration_health_success(self):
        """Test successful integration health check."""
        user_id = "user_123"
        provider = "google"

        mock_response = {
            "integration_id": "integration_123",
            "provider": "google",
            "status": "healthy",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "details": {"access_token_valid": True, "refresh_token_valid": True},
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.check_integration_health = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/{user_id}/integrations/{provider}/health",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["integration_id"] == mock_response["integration_id"]
        assert data["provider"] == mock_response["provider"]
        assert data["status"] == mock_response["status"]

    def test_get_integration_statistics_success(self):
        """Test successful integration statistics retrieval."""
        user_id = "user_123"

        mock_response = {
            "total_integrations": 3,
            "active_integrations": 2,
            "error_integrations": 1,
            "providers": {
                "google": {"count": 2, "active": 1, "errors": 1},
                "microsoft": {"count": 1, "active": 1, "errors": 0},
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_integration_statistics = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/v1/users/{user_id}/integrations/stats",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_integrations"] == mock_response["total_integrations"]
        assert data["active_integrations"] == mock_response["active_integrations"]
        assert data["error_integrations"] == mock_response["error_integrations"]
        assert "google" in data["providers"]
        assert "microsoft" in data["providers"]


class TestProviderEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for provider-specific endpoints."""

    def test_list_oauth_providers_success(self):
        """Test successful OAuth provider listing."""
        mock_providers = {
            "google": {
                "name": "Google",
                "scopes": ["email", "profile", "calendar"],
                "default_scopes": ["email", "profile"],
            },
            "microsoft": {
                "name": "Microsoft",
                "scopes": ["User.Read", "Calendars.Read"],
                "default_scopes": ["User.Read"],
            },
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.get_oauth_providers = AsyncMock(
                return_value=mock_providers
            )

            def get_provider_config_side_effect(provider):
                if provider == "google":
                    return {
                        "name": "Google",
                        "scopes": ["email", "profile", "calendar"],
                        "default_scopes": ["email", "profile"],
                    }
                elif provider == "microsoft":
                    return {
                        "name": "Microsoft",
                        "scopes": ["User.Read", "Calendars.Read"],
                        "default_scopes": ["User.Read"],
                    }
                else:
                    raise ValueError(f"Unknown provider: {provider}")

            mock_service.return_value.get_provider_config = AsyncMock(
                side_effect=get_provider_config_side_effect
            )

            response = self.client.get(
                "/v1/users/me/integrations/providers",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "google" in data
        assert "microsoft" in data
        assert data["google"]["name"] == "Google"
        assert data["microsoft"]["name"] == "Microsoft"

    def test_validate_oauth_scopes_success(self):
        """Test successful OAuth scope validation."""
        provider = "google"
        scopes = ["email", "profile", "calendar"]

        mock_response = {
            "valid": True,
            "valid_scopes": ["email", "profile", "calendar"],
            "invalid_scopes": [],
            "warnings": [],
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.validate_oauth_scopes = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                f"/v1/users/me/integrations/{provider}/scopes",
                json={"scopes": scopes},
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert len(data["valid_scopes"]) == 3
        assert len(data["invalid_scopes"]) == 0

    def test_validate_oauth_scopes_unavailable_provider(self):
        """Test OAuth scope validation with unavailable provider."""
        provider = "invalid_provider"
        scopes = ["email", "profile"]

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.validate_oauth_scopes.side_effect = ValueError(
                "Provider not available"
            )
            response = self.client.post(
                f"/v1/users/me/integrations/{provider}/scopes",
                json={"scopes": scopes},
                headers={"Authorization": "Bearer valid-token"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Provider not available" in data["message"]


class TestIntegrationEndpointSecurity(BaseUserManagementIntegrationTest):
    """Test cases for integration endpoint security."""

    def test_endpoints_require_authentication(self):
        """Test that all integration endpoints require authentication."""
        user_id = "user_123"
        provider = "google"

        # Clear any auth overrides to test unauthenticated access
        self.app.dependency_overrides.clear()

        # Test various endpoints without authentication
        endpoints = [
            f"/v1/users/{user_id}/integrations/",
            f"/v1/users/{user_id}/integrations/oauth/start",
            f"/v1/users/{user_id}/integrations/{provider}",
            f"/v1/users/{user_id}/integrations/{provider}/refresh",
            f"/v1/users/{user_id}/integrations/{provider}/health",
            f"/v1/users/{user_id}/integrations/stats",
            "/v1/users/me/integrations/providers",
            f"/v1/users/me/integrations/{provider}/scopes",
        ]

        for endpoint in endpoints:
            if "start" in endpoint:
                response = self.client.post(endpoint, json={})
            elif "refresh" in endpoint or "scopes" in endpoint:
                response = self.client.put(endpoint, json={})
            elif "health" in endpoint or "stats" in endpoint or "providers" in endpoint:
                response = self.client.get(endpoint)
            elif "oauth/callback" in endpoint:
                response = self.client.post(endpoint, json={})
            else:
                response = self.client.get(endpoint)

            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ], f"Endpoint {endpoint} should require authentication"

    def test_user_ownership_verification(self):
        """Test that users can only access their own integrations."""
        user_id = "user_123"

        async def mock_different_user():
            return "different_user_456"

        # Override auth to return a different user
        from services.user.auth.nextauth import get_current_user

        self.app.dependency_overrides[get_current_user] = mock_different_user

        response = self.client.get(
            f"/v1/users/{user_id}/integrations/",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
