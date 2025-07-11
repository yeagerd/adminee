"""
Unit tests for integration management endpoints.

Tests OAuth flow management, integration status, token operations,
health monitoring, and provider configuration endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status

from services.common.http_errors import NotFoundError, ServiceError
from services.user.models.integration import (
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.schemas.integration import (
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationStatsResponse,
    OAuthCallbackResponse,
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
                f"/users/{user_id}/integrations/",
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
                f"/users/{user_id}/integrations/",
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
        response = self.client.get(f"/users/{user_id}/integrations/")
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
            import pytest

            with pytest.raises(NotFoundError) as exc_info:
                self.client.get(
                    f"/users/{user_id}/integrations/",
                    headers={"Authorization": "Bearer valid-token"},
                )
            assert "User not found" in str(exc_info.value)


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
                f"/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["requested_scopes"] == ["email", "profile"]

    def test_start_oauth_flow_microsoft_success(self):
        """Test successful OAuth flow initiation for Microsoft."""
        user_id = "user_123"

        request_data = {
            "provider": "microsoft",
            "redirect_uri": "https://app.example.com/oauth/microsoft/callback",
            "scopes": ["User.Read", "Mail.Read"],  # Example additional scopes
            "state_data": {"custom_return_url": "/settings/integrations"},
        }

        mock_response_data = {
            "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=msft-client-id&state=mock_ms_state&...",
            "state": "mock_ms_state",
            "provider": "microsoft",
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "requested_scopes": [
                "openid",
                "email",
                "profile",
                "User.Read",
                "Mail.Read",
            ],
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.start_oauth_flow = AsyncMock(
                return_value=mock_response_data
            )
            response = self.client.post(
                f"/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["provider"] == "microsoft"
        assert "User.Read" in data["requested_scopes"]
        assert "Mail.Read" in data["requested_scopes"]

    def test_start_oauth_flow_invalid_provider(self):
        """Test OAuth flow initiation with invalid provider."""
        user_id = "user_123"

        request_data = {
            "provider": "invalid_provider",
            "redirect_uri": "https://app.example.com/oauth/callback",
        }

        response = self.client.post(
            f"/users/{user_id}/integrations/oauth/start",
            json=request_data,
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_complete_oauth_flow_success(self):
        """Test successful OAuth flow completion."""
        mock_response = OAuthCallbackResponse(
            success=True,
            integration_id=1,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            scopes=["email", "profile"],
            external_user_info={"email": "user@example.com"},
            error=None,
        )

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/users/user_123/integrations/oauth/callback?provider=google",
                json={
                    "code": "auth_code_123",
                    "state": "state_123",
                },
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "google"
        assert data["integration_id"] == 1

    def test_complete_oauth_flow_microsoft_success(self):
        """Test successful OAuth flow completion for Microsoft."""
        mock_response = OAuthCallbackResponse(
            success=True,
            integration_id=2,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.ACTIVE,
            scopes=["openid", "email", "profile", "User.Read"],
            external_user_info={
                "email": "user@example.com",
                "displayName": "Test User",
                "id": "ms_user_id_123",
            },
            error=None,
        )

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/users/user_123/integrations/oauth/callback?provider=microsoft",
                json={
                    "code": "ms_auth_code_456",
                    "state": "ms_state_456",
                },
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "microsoft"
        assert data["integration_id"] == 2
        assert "User.Read" in data["scopes"]
        assert data["external_user_info"]["displayName"] == "Test User"

    @patch("services.user.services.audit_service.audit_logger.log_audit_event")
    def test_complete_oauth_flow_with_error(self, mock_audit):
        """Test OAuth flow completion with error."""
        mock_response = OAuthCallbackResponse(
            success=False,
            integration_id=None,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ERROR,
            scopes=[],
            external_user_info=None,
            error="OAuth flow failed: Invalid authorization code",
        )

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.complete_oauth_flow = AsyncMock(
                return_value=mock_response
            )
            response = self.client.post(
                "/users/user_123/integrations/oauth/callback?provider=google",
                json={
                    "code": "invalid_code",
                    "state": "state_123",
                },
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "OAuth flow failed" in data["error"]

    def test_complete_oauth_flow_service_error(self):
        """Test OAuth flow completion with service error."""
        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.complete_oauth_flow = AsyncMock(
                side_effect=ServiceError("Service unavailable")
            )
            import pytest

            with pytest.raises(ServiceError) as exc_info:
                self.client.post(
                    "/users/user_123/integrations/oauth/callback?provider=google",
                    json={
                        "code": "auth_code_123",
                        "state": "state_123",
                    },
                    headers={"Authorization": "Bearer valid-token"},
                )
            assert "Service unavailable" in str(exc_info.value)


class TestIntegrationManagementEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for integration management operations."""

    def test_disconnect_integration_success(self):
        """Test successful integration disconnection."""
        user_id = "user_123"
        provider = "google"

        mock_response = {
            "success": True,
            "integration_id": 1,
            "provider": "google",
            "tokens_revoked": True,
            "data_deleted": False,
            "disconnected_at": datetime.now(timezone.utc),
            "error": None,
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.disconnect_integration = AsyncMock(
                return_value=mock_response
            )
            response = self.client.delete(
                f"/users/{user_id}/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == provider
        assert data["tokens_revoked"] is True

    def test_disconnect_integration_not_found(self):
        """Test disconnection of non-existent integration."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.disconnect_integration = AsyncMock(
                side_effect=NotFoundError("Integration not found")
            )
            import pytest

            with pytest.raises(NotFoundError) as exc_info:
                self.client.delete(
                    f"/users/{user_id}/integrations/{provider}",
                    headers={"Authorization": "Bearer valid-token"},
                )
            assert "Integration not found" in str(exc_info.value)

    def test_refresh_integration_tokens_success(self):
        """Test successful token refresh."""
        user_id = "user_123"
        provider = "google"

        mock_response = {
            "success": True,
            "integration_id": 1,
            "provider": provider,
            "token_expires_at": datetime.now(timezone.utc).isoformat(),
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.refresh_integration_tokens = AsyncMock(
                return_value=mock_response
            )
            response = self.client.put(
                f"/users/{user_id}/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == provider

    def test_refresh_integration_tokens_failure(self):
        """Test token refresh failure."""
        user_id = "user_123"
        provider = "google"

        mock_response = {
            "success": False,
            "integration_id": 1,
            "provider": provider,
            "token_expires_at": None,
            "refreshed_at": None,
            "error": "Token refresh failed",
        }

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.refresh_integration_tokens = AsyncMock(
                return_value=mock_response
            )
            response = self.client.put(
                f"/users/{user_id}/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Token refresh failed"

    def test_check_integration_health_success(self):
        """Test successful integration health check."""
        user_id = "user_123"
        provider = "google"

        mock_response = IntegrationHealthResponse(
            integration_id=1,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            healthy=True,
            last_check_at=datetime.now(timezone.utc),
            issues=[],
            recommendations=[],
        )

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.check_integration_health = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/users/{user_id}/integrations/{provider}/health",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == provider
        assert data["healthy"] is True
        assert data["status"] == "active"

    def test_get_integration_statistics_success(self):
        """Test successful integration statistics retrieval."""
        user_id = "user_123"

        mock_response = IntegrationStatsResponse(
            total_integrations=3,
            active_integrations=2,
            failed_integrations=1,
            pending_integrations=0,
            by_provider={
                "google": 1,
                "microsoft": 1,
                "slack": 1,
            },
            by_status={
                "active": 2,
                "error": 1,
                "inactive": 0,
                "pending": 0,
            },
            recent_errors=[
                {
                    "provider": "slack",
                    "error": "Token expired",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            sync_stats={
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "successful_syncs": 15,
                "failed_syncs": 2,
            },
        )

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:

            mock_service.return_value.get_integration_statistics = AsyncMock(
                return_value=mock_response
            )
            response = self.client.get(
                f"/users/{user_id}/integrations/stats",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_integrations"] == 3
        assert data["active_integrations"] == 2
        assert data["failed_integrations"] == 1
        assert data["pending_integrations"] == 0
        assert "google" in data["by_provider"]
        assert data["by_provider"]["google"] == 1


class TestProviderEndpoints(BaseUserManagementIntegrationTest):
    """Test cases for provider configuration endpoints."""

    def test_list_oauth_providers_success(self):
        """Test successful OAuth provider listing."""
        # Mock OAuth config
        mock_oauth_config = MagicMock()
        mock_oauth_config.get_available_providers.return_value = [
            "google",
            "microsoft",
            "slack",
        ]
        mock_provider_config = MagicMock()
        mock_provider_config.name = "google"
        mock_provider_config.display_name = "Google"
        mock_provider_config.description = "Google OAuth integration"
        mock_provider_config.scopes = ["email", "profile"]
        mock_provider_config.required_scopes = ["email"]
        mock_oauth_config.get_provider_config.return_value = mock_provider_config

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.oauth_config = mock_oauth_config
            response = self.client.get(
                "/integrations/providers",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "providers" in data
        assert data["total"] >= 0

    def test_validate_oauth_scopes_success(self):
        """Test successful OAuth scope validation."""

        request_data = {
            "provider": "google",
            "scopes": ["email", "profile", "invalid_scope"],
        }

        # Mock OAuth config
        mock_oauth_config = MagicMock()
        mock_oauth_config.is_provider_available.return_value = True
        mock_provider_config = MagicMock()
        mock_provider_config.validate_scopes.return_value = (
            ["email", "profile"],
            ["invalid_scope"],
        )
        mock_provider_config.scope_definitions = {
            "email": {"required": True, "sensitive": False},
            "profile": {"required": False, "sensitive": False},
        }
        mock_oauth_config.get_provider_config.return_value = mock_provider_config

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.oauth_config = mock_oauth_config
            response = self.client.post(
                "/integrations/validate-scopes",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "google"
        assert "email" in data["valid_scopes"]
        assert "invalid_scope" in data["invalid_scopes"]
        assert len(data["warnings"]) > 0

    def test_validate_oauth_scopes_unavailable_provider(self):
        """Test scope validation for unavailable provider."""

        request_data = {
            "provider": "google",
            "scopes": ["email", "profile"],
        }

        # Mock OAuth config
        mock_oauth_config = MagicMock()
        mock_oauth_config.is_provider_available.return_value = False

        with patch(
            "services.user.routers.integrations.get_integration_service"
        ) as mock_service:
            mock_service.return_value.oauth_config = mock_oauth_config
            import pytest

            from services.common.http_errors import ValidationError

            with pytest.raises(ValidationError) as exc_info:
                self.client.post(
                    "/integrations/validate-scopes",
                    json=request_data,
                    headers={"Authorization": "Bearer valid-token"},
                )
            assert "Provider google is not available" in str(exc_info.value)


class TestIntegrationEndpointSecurity(BaseUserManagementIntegrationTest):
    """Test cases for integration endpoint security."""

    def test_endpoints_require_authentication(self):
        """Test that endpoints require proper authentication."""
        # Clear authentication override to test unauthenticated access
        from services.user.auth.nextauth import get_current_user

        if get_current_user in self.app.dependency_overrides:
            del self.app.dependency_overrides[get_current_user]

        # Test various endpoints without authentication
        # These endpoints require user_id and authentication
        user_id = "test_user_123"

        # Test GET endpoints
        get_endpoints = [
            f"/users/{user_id}/integrations/",
            f"/users/{user_id}/integrations/stats",
        ]

        for endpoint in get_endpoints:
            response = self.client.get(endpoint)
            # Should return 401 (Unauthorized), 403 (Forbidden), or 422 (Validation Error)
            assert response.status_code in [
                401,
                403,
                422,
            ], f"GET endpoint {endpoint} should require authentication, got {response.status_code}"

        # Test POST endpoints
        post_endpoints = [
            f"/users/{user_id}/integrations/oauth/start",
        ]

        for endpoint in post_endpoints:
            response = self.client.post(endpoint, json={})
            # Should return 401 (Unauthorized), 403 (Forbidden), or 422 (Validation Error)
            assert response.status_code in [
                401,
                403,
                422,
            ], f"POST endpoint {endpoint} should require authentication, got {response.status_code}"

    def test_user_ownership_verification(self):
        """Test that users can only access their own resources."""
        from services.user.auth.nextauth import get_current_user

        # Mock a different user
        async def mock_different_user():
            return "different_user_456"

        self.app.dependency_overrides[get_current_user] = mock_different_user

        # Try to access integrations for a different user (should fail ownership check)
        user_id = "test_user_123"  # Different from the mocked user
        response = self.client.get(f"/users/{user_id}/integrations/")
        # This should fail due to ownership verification
        assert response.status_code in [403, 404, 500]  # Various valid error responses
