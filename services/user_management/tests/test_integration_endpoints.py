"""
Unit tests for integration management endpoints.

Tests OAuth flow management, integration status, token operations,
health monitoring, and provider configuration endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..auth.clerk import get_current_user
from ..exceptions import (
    IntegrationException,
    NotFoundException,
)
from ..main import app
from ..models.integration import IntegrationProvider, IntegrationStatus
from ..schemas.integration import (
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationStatsResponse,
    OAuthCallbackResponse,
)


class TestIntegrationListEndpoint:
    """Test cases for listing user integrations."""

    def test_list_integrations_success(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test successful integration listing."""
        user_id = "user_123"

        # Mock integration service response
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
            "services.user_management.services.integration_service.integration_service.get_user_integrations",
            return_value=mock_response,
        ):
            response = client.get(
                f"/users/{user_id}/integrations/",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["active_count"] == 1
        assert len(data["integrations"]) == 1
        assert data["integrations"][0]["provider"] == "google"

    def test_list_integrations_with_filters(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test integration listing with query filters."""
        user_id = "user_123"

        mock_response = IntegrationListResponse(
            integrations=[],
            total=0,
            active_count=0,
            error_count=0,
        )

        with patch(
            "services.user_management.services.integration_service.integration_service.get_user_integrations",
            return_value=mock_response,
        ) as mock_service:
            response = client.get(
                f"/users/{user_id}/integrations/",
                params={
                    "provider": "google",
                    "status": "active",
                    "include_token_info": "false",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        mock_service.assert_called_once_with(
            user_id=user_id,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            include_token_info=False,
        )

    def test_list_integrations_unauthorized(self, client: TestClient):
        """Test integration listing without authentication."""
        user_id = "user_123"
        response = client.get(f"/users/{user_id}/integrations/")
        # The actual status depends on the auth implementation
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_integrations_user_not_found(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test integration listing for non-existent user."""
        user_id = "user_123"

        with patch(
            "services.user_management.services.integration_service.integration_service.get_user_integrations",
            side_effect=NotFoundException("User not found"),
        ):
            response = client.get(
                f"/users/{user_id}/integrations/",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestOAuthFlowEndpoints:
    """Test cases for OAuth flow management."""

    def test_start_oauth_flow_success(self, client: TestClient, mock_auth_dependencies):
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
            "services.user_management.services.integration_service.integration_service.start_oauth_flow",
            return_value=mock_response,
        ):
            response = client.post(
                f"/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["requested_scopes"] == ["email", "profile"]

    def test_start_oauth_flow_microsoft_success(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test successful OAuth flow initiation for Microsoft."""
        user_id = "user_123"

        request_data = {
            "provider": "microsoft",
            "redirect_uri": "https://app.example.com/oauth/microsoft/callback",
            "scopes": ["User.Read", "Mail.Read"], # Example additional scopes
            "state_data": {"custom_return_url": "/settings/integrations"},
        }

        mock_response_data = {
            "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=msft-client-id&state=mock_ms_state&...",
            "state": "mock_ms_state",
            "provider": "microsoft",
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "requested_scopes": ["openid", "email", "profile", "offline_access", "https://graph.microsoft.com/User.Read", "User.Read", "Mail.Read"],
        }

        # Ensure the integration_service path matches your project structure
        with patch(
            "services.user_management.services.integration_service.integration_service.start_oauth_flow",
            new_callable=AsyncMock, # Use AsyncMock for async methods
            return_value=mock_response_data,
        ) as mock_start_flow:
            response = client.post(
                f"/users/{user_id}/integrations/oauth/start",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"}, # Handled by mock_auth_dependencies
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorization_url"].startswith(
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        assert data["state"] == "mock_ms_state"
        assert data["provider"] == "microsoft"
        assert "User.Read" in data["requested_scopes"]
        assert "Mail.Read" in data["requested_scopes"]

        mock_start_flow.assert_called_once_with(
            user_id=user_id,
            provider=IntegrationProvider.MICROSOFT,
            redirect_uri=request_data["redirect_uri"],
            scopes=request_data["scopes"],
            state_data=request_data["state_data"],
        )

    def test_start_oauth_flow_invalid_provider(self, client: TestClient, mock_auth):
        """Test OAuth flow start with invalid provider."""
        user_id = "user_123"

        request_data = {
            "provider": "invalid_provider",
            "redirect_uri": "https://app.example.com/oauth/callback",
        }

        response = client.post(
            f"/users/{user_id}/integrations/oauth/start",
            json=request_data,
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_complete_oauth_flow_success(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test successful OAuth flow completion."""
        user_id = "user_123"

        request_data = {
            "code": "auth_code_123",
            "state": "state_abc123",
        }

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": "google",
            "status": "active",
            "scopes": ["email", "profile"],
            "external_user_info": {"email": "user@example.com"},
            "error": None,
        }

        with patch(
            "services.user_management.services.integration_service.integration_service.complete_oauth_flow",
            return_value=mock_response,
        ):
            response = client.post(
                f"/users/{user_id}/integrations/oauth/callback?provider=google",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["integration_id"] == 123
        assert data["provider"] == "google"

    def test_complete_oauth_flow_microsoft_success(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test successful OAuth flow completion for Microsoft."""
        user_id = "user_123"

        request_data = {
            "code": "msft_auth_code_xyz",
            "state": "mock_ms_state_xyz",
            # Optional: include error fields if testing error responses from provider
            # "error": None,
            # "error_description": None,
        }

        mock_response_data = {
            "success": True,
            "integration_id": "ms-integration-id-456",
            "provider": "microsoft",
            "status": "active",
            "scopes": ["openid", "email", "profile", "offline_access", "https://graph.microsoft.com/User.Read", "User.Read"],
            "external_user_info": {"userPrincipalName": "user@example.com", "id": "ms-user-guid"},
            "error": None,
        }

        with patch(
            "services.user_management.services.integration_service.integration_service.complete_oauth_flow",
            new_callable=AsyncMock,
            return_value=mock_response_data,
        ) as mock_complete_flow:
            response = client.post(
                f"/users/{user_id}/integrations/oauth/callback?provider=microsoft", # Provider as query param
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["integration_id"] == "ms-integration-id-456"
        assert data["provider"] == "microsoft"
        assert data["status"] == "active"
        assert "User.Read" in data["scopes"]

        mock_complete_flow.assert_called_once_with(
            user_id=user_id,
            provider=IntegrationProvider.MICROSOFT,
            code=request_data["code"],
            state=request_data["state"],
            error=None, # Explicitly pass None if not testing error case
            error_description=None, # Explicitly pass None
        )

    @patch(
        "services.user_management.services.audit_service.audit_logger.log_audit_event"
    )
    def test_complete_oauth_flow_with_error(
        self, mock_audit, client: TestClient, mock_auth
    ):
        """Test OAuth flow completion with OAuth error."""
        # Mock audit logging to prevent database errors
        mock_audit.return_value = None

        user_id = "user_123"

        request_data = {
            "error": "access_denied",
            "error_description": "User denied access",
            "state": "state_abc123",
        }

        response = client.post(
            f"/users/{user_id}/integrations/oauth/callback?provider=google",
            json=request_data,
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "access_denied" in data["error"]

    def test_complete_oauth_flow_service_error(self, client: TestClient, mock_auth):
        """Test OAuth flow completion with service error."""
        user_id = "user_123"

        request_data = {
            "code": "auth_code_123",
            "state": "state_abc123",
        }

        # Mock the service to return an error response instead of raising exception
        mock_error_response = OAuthCallbackResponse(
            success=False,
            integration_id=None,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ERROR,
            scopes=[],
            external_user_info=None,
            error="Token exchange failed",
        )

        with patch(
            "services.user_management.services.integration_service.integration_service.complete_oauth_flow",
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ):
            response = client.post(
                f"/users/{user_id}/integrations/oauth/callback?provider=google",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "Token exchange failed" in data["error"]


class TestIntegrationManagementEndpoints:
    """Test cases for integration management operations."""

    def test_disconnect_integration_success(self, client: TestClient, mock_auth):
        """Test successful integration disconnection."""
        user_id = "user_123"
        provider = "google"

        request_data = {
            "revoke_tokens": True,
            "delete_data": False,
        }

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": "google",
            "tokens_revoked": True,
            "data_deleted": False,
            "disconnected_at": datetime.now(timezone.utc),
            "error": None,
        }

        with patch(
            "services.user_management.services.integration_service.integration_service.disconnect_integration",
            return_value=mock_response,
        ):
            response = client.request(
                "DELETE",
                f"/users/{user_id}/integrations/{provider}",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["tokens_revoked"] is True

    def test_disconnect_integration_not_found(self, client: TestClient, mock_auth):
        """Test disconnection of non-existent integration."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user_management.services.integration_service.integration_service.disconnect_integration",
            side_effect=NotFoundException("Integration not found"),
        ):
            response = client.delete(
                f"/users/{user_id}/integrations/{provider}",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_refresh_integration_tokens_success(self, client: TestClient, mock_auth):
        """Test successful token refresh."""
        user_id = "user_123"
        provider = "google"

        request_data = {"force": True}

        mock_response = {
            "success": True,
            "integration_id": 123,
            "provider": "google",
            "token_expires_at": datetime.now(timezone.utc),
            "refreshed_at": datetime.now(timezone.utc),
            "error": None,
        }

        with patch(
            "services.user_management.services.integration_service.integration_service.refresh_integration_tokens",
            return_value=mock_response,
        ):
            response = client.put(
                f"/users/{user_id}/integrations/{provider}/refresh",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "google"

    def test_refresh_integration_tokens_failure(self, client: TestClient, mock_auth):
        """Test token refresh failure."""
        user_id = "user_123"
        provider = "google"

        with patch(
            "services.user_management.services.integration_service.integration_service.refresh_integration_tokens",
            side_effect=IntegrationException("Refresh token expired"),
        ):
            response = client.put(
                f"/users/{user_id}/integrations/{provider}/refresh",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "Refresh token expired" in data["error"]

    def test_check_integration_health_success(self, client: TestClient, mock_auth):
        """Test successful integration health check."""
        user_id = "user_123"
        provider = "google"

        mock_response = IntegrationHealthResponse(
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            healthy=True,
            last_check_at=datetime.now(timezone.utc),
            issues=[],
            recommendations=[],
        )

        with patch(
            "services.user_management.services.integration_service.integration_service.check_integration_health",
            return_value=mock_response,
        ):
            response = client.get(
                f"/users/{user_id}/integrations/{provider}/health",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["healthy"] is True
        assert data["provider"] == "google"
        assert len(data["issues"]) == 0

    def test_get_integration_statistics_success(self, client: TestClient, mock_auth):
        """Test successful integration statistics retrieval."""
        user_id = "user_123"

        mock_response = IntegrationStatsResponse(
            total_integrations=2,
            active_integrations=1,
            failed_integrations=1,
            pending_integrations=0,
            by_provider={
                "google": 1,
                "microsoft": 1,
            },
            by_status={
                "active": 1,
                "error": 1,
                "inactive": 0,
                "pending": 0,
            },
            recent_errors=[
                {
                    "provider": "microsoft",
                    "error": "Token expired",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            sync_stats={
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "successful_syncs": 10,
                "failed_syncs": 1,
            },
        )

        with patch(
            "services.user_management.services.integration_service.integration_service.get_integration_statistics",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.get(
                f"/users/{user_id}/integrations/stats",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_integrations"] == 2
        assert data["active_integrations"] == 1
        assert data["failed_integrations"] == 1
        assert data["pending_integrations"] == 0
        assert data["by_provider"]["google"] == 1
        assert data["by_provider"]["microsoft"] == 1
        assert data["by_status"]["active"] == 1
        assert data["by_status"]["error"] == 1
        assert data["by_status"]["inactive"] == 0
        assert data["by_status"]["pending"] == 0
        assert len(data["recent_errors"]) == 1


class TestProviderEndpoints:
    """Test cases for OAuth provider management."""

    def test_list_oauth_providers_success(
        self, client: TestClient, mock_auth_dependencies
    ):
        """Test successful OAuth provider listing."""

        # Mock OAuth config
        mock_oauth_config = MagicMock()
        mock_oauth_config.is_provider_available.return_value = True
        mock_provider_config = MagicMock()
        mock_provider_config.name = "Google"
        mock_provider_config.default_scopes = ["email", "profile"]
        mock_provider_config.scope_definitions = {
            "email": {"description": "Access email address", "required": True},
            "profile": {"description": "Access profile information", "required": False},
        }
        mock_oauth_config.get_provider_config.return_value = mock_provider_config

        with patch(
            "services.user_management.services.integration_service.integration_service.oauth_config",
            mock_oauth_config,
        ):
            response = client.get(
                "/integrations/providers",
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "providers" in data
        assert data["total"] >= 0

    def test_validate_oauth_scopes_success(self, client: TestClient, mock_auth):
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
            "services.user_management.services.integration_service.integration_service.oauth_config",
            mock_oauth_config,
        ):
            response = client.post(
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

    def test_validate_oauth_scopes_unavailable_provider(
        self, client: TestClient, mock_auth
    ):
        """Test scope validation for unavailable provider."""

        request_data = {
            "provider": "google",
            "scopes": ["email", "profile"],
        }

        # Mock OAuth config
        mock_oauth_config = MagicMock()
        mock_oauth_config.is_provider_available.return_value = False

        with patch(
            "services.user_management.services.integration_service.integration_service.oauth_config",
            mock_oauth_config,
        ):
            response = client.post(
                "/integrations/validate-scopes",
                json=request_data,
                headers={"Authorization": "Bearer valid-token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestIntegrationEndpointSecurity:
    """Test cases for integration endpoint security."""

    def test_endpoints_require_authentication(self, client: TestClient):
        """Test that all integration endpoints require authentication."""
        user_id = "user_123"

        endpoints = [
            ("GET", f"/users/{user_id}/integrations/"),
            ("POST", f"/users/{user_id}/integrations/oauth/start"),
            ("POST", f"/users/{user_id}/integrations/oauth/callback?provider=google"),
            ("DELETE", f"/users/{user_id}/integrations/google"),
            ("PUT", f"/users/{user_id}/integrations/google/refresh"),
            ("GET", f"/users/{user_id}/integrations/google/health"),
            ("GET", f"/users/{user_id}/integrations/stats"),
            ("GET", "/integrations/providers"),
            ("POST", "/integrations/validate-scopes"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_422_UNPROCESSABLE_ENTITY,  # For invalid request data
            ]

    def test_user_ownership_verification(self, client: TestClient, mock_auth):
        """Test that users can only access their own integrations."""
        user_id = "user_123"
        other_user_id = "user_456"

        # Override the mock to return a different user
        async def mock_different_user():
            return other_user_id

        app.dependency_overrides[get_current_user] = mock_different_user

        with patch(
            "services.user_management.auth.clerk.verify_user_ownership",
            side_effect=Exception("Access denied"),
        ):
            response = client.get(
                f"/users/{user_id}/integrations/",
                headers={"Authorization": "Bearer valid-token"},
            )

        # Clean up
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_auth_dependencies():
    """Mock authentication dependencies."""

    async def mock_get_current_user():
        return "user_123"

    async def mock_verify_user_ownership(current_user_id: str, resource_user_id: str):
        return None  # No exception means authorized

    # Override dependencies in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Mock the verify_user_ownership function
    with patch(
        "services.user_management.auth.clerk.verify_user_ownership",
        side_effect=mock_verify_user_ownership,
    ) as mock_verify:

        yield {
            "get_user": mock_get_current_user,
            "verify": mock_verify,
        }

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_auth():
    """Mock authentication for simple tests."""

    async def mock_get_current_user():
        return "user_123"

    async def mock_verify_user_ownership(current_user_id: str, resource_user_id: str):
        return None  # No exception means authorized

    # Override dependencies in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Mock the verify_user_ownership function
    with patch(
        "services.user_management.auth.clerk.verify_user_ownership",
        side_effect=mock_verify_user_ownership,
    ) as mock_verify:
        yield mock_verify

    # Clean up
    app.dependency_overrides.clear()
