"""
Unit tests for integration schemas.

Tests all Pydantic models for integration management including validation,
serialization, and error handling.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from services.user_management.models.integration import IntegrationProvider, IntegrationStatus
from services.user_management.schemas.integration import (
    IntegrationDisconnectRequest,
    IntegrationDisconnectResponse,
    IntegrationErrorResponse,
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationProviderInfo,
    IntegrationResponse,
    IntegrationScopeResponse,
    IntegrationStatsResponse,
    IntegrationSyncRequest,
    IntegrationSyncResponse,
    IntegrationUpdateRequest,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    ProviderListResponse,
    ScopeValidationRequest,
    ScopeValidationResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)


class TestIntegrationScopeResponse:
    """Test IntegrationScopeResponse schema."""

    def test_scope_response_creation(self):
        """Test creating scope response."""
        scope = IntegrationScopeResponse(
            name="email",
            description="Access to user email",
            required=True,
            sensitive=False,
            granted=True,
        )

        assert scope.name == "email"
        assert scope.description == "Access to user email"
        assert scope.required is True
        assert scope.sensitive is False
        assert scope.granted is True

    def test_scope_response_defaults(self):
        """Test scope response default values."""
        scope = IntegrationScopeResponse(
            name="profile",
            description="Basic profile",
            required=False,
            sensitive=False,
            granted=False,
        )

        assert scope.required is False
        assert scope.sensitive is False


class TestIntegrationProviderInfo:
    """Test IntegrationProviderInfo schema."""

    def test_provider_info_creation(self):
        """Test creating provider info."""
        scopes = [
            IntegrationScopeResponse(
                name="email",
                description="Email access",
                required=True,
                sensitive=False,
                granted=True,
            )
        ]

        provider_info = IntegrationProviderInfo(
            name="Google",
            provider=IntegrationProvider.GOOGLE,
            available=True,
            supported_scopes=scopes,
            default_scopes=["email", "profile"],
        )

        assert provider_info.name == "Google"
        assert provider_info.provider == IntegrationProvider.GOOGLE
        assert provider_info.available is True
        assert len(provider_info.supported_scopes) == 1
        assert provider_info.default_scopes == ["email", "profile"]

    def test_provider_info_defaults(self):
        """Test provider info default values."""
        provider_info = IntegrationProviderInfo(
            name="Microsoft",
            provider=IntegrationProvider.MICROSOFT,
            available=False,
        )

        assert provider_info.supported_scopes == []
        assert provider_info.default_scopes == []


class TestIntegrationResponse:
    """Test IntegrationResponse schema."""

    def test_integration_response_creation(self):
        """Test creating integration response."""
        now = datetime.now(timezone.utc)

        integration = IntegrationResponse(
            id=1,
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            scopes=["email", "profile"],
            external_user_id="google123",
            external_email="user@gmail.com",
            external_name="Test User",
            has_access_token=True,
            has_refresh_token=True,
            token_expires_at=now,
            token_created_at=now,
            last_sync_at=now,
            last_error=None,
            error_count=0,
            created_at=now,
            updated_at=now,
        )

        assert integration.id == 1
        assert integration.user_id == "user123"
        assert integration.provider == IntegrationProvider.GOOGLE
        assert integration.status == IntegrationStatus.ACTIVE
        assert integration.scopes == ["email", "profile"]
        assert integration.external_user_id == "google123"
        assert integration.has_access_token is True
        assert integration.has_refresh_token is True
        assert integration.error_count == 0

    def test_integration_response_defaults(self):
        """Test integration response default values."""
        now = datetime.now(timezone.utc)

        integration = IntegrationResponse(
            id=1,
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            has_access_token=True,
            has_refresh_token=False,
            created_at=now,
            updated_at=now,
        )

        assert integration.scopes == []
        assert integration.external_user_id is None
        assert integration.external_email is None
        assert integration.external_name is None
        assert integration.token_expires_at is None
        assert integration.token_created_at is None
        assert integration.last_sync_at is None
        assert integration.last_error is None
        assert integration.error_count == 0


class TestOAuthStartRequest:
    """Test OAuthStartRequest schema."""

    def test_oauth_start_request_creation(self):
        """Test creating OAuth start request."""
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile"],
            state_data={"key": "value"},
        )

        assert request.provider == IntegrationProvider.GOOGLE
        assert request.redirect_uri == "https://example.com/callback"
        assert set(request.scopes) == {"email", "profile"}
        assert request.state_data == {"key": "value"}

    def test_oauth_start_request_defaults(self):
        """Test OAuth start request default values."""
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        assert request.scopes is None
        assert request.state_data is None

    def test_oauth_start_request_redirect_uri_validation(self):
        """Test redirect URI validation."""
        # Valid HTTPS URI
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )
        assert request.redirect_uri == "https://example.com/callback"

        # Valid HTTP URI
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="http://localhost:3000/callback",
        )
        assert request.redirect_uri == "http://localhost:3000/callback"

        # Invalid URI
        with pytest.raises(ValidationError) as exc_info:
            OAuthStartRequest(
                provider=IntegrationProvider.GOOGLE,
                redirect_uri="invalid-uri",
            )
        assert "URL scheme must be one of" in str(exc_info.value)

    def test_oauth_start_request_scope_validation(self):
        """Test scope validation and cleanup."""
        # Remove duplicates and empty strings
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile", "email", "", "  ", "calendar"],
        )
        # Should remove duplicates and empty/whitespace strings
        expected_scopes = {"email", "profile", "calendar"}
        assert set(request.scopes) == expected_scopes

        # Empty list becomes None
        request = OAuthStartRequest(
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            scopes=["", "  "],
        )
        assert request.scopes is None


class TestOAuthStartResponse:
    """Test OAuthStartResponse schema."""

    def test_oauth_start_response_creation(self):
        """Test creating OAuth start response."""
        now = datetime.now(timezone.utc)

        response = OAuthStartResponse(
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://accounts.google.com/oauth2/auth?...",
            state="random-state-string",
            expires_at=now,
            requested_scopes=["email", "profile"],
        )

        assert response.provider == IntegrationProvider.GOOGLE
        assert "accounts.google.com" in response.authorization_url
        assert response.state == "random-state-string"
        assert response.expires_at == now
        assert response.requested_scopes == ["email", "profile"]

    def test_oauth_start_response_defaults(self):
        """Test OAuth start response default values."""
        now = datetime.now(timezone.utc)

        response = OAuthStartResponse(
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://accounts.google.com/oauth2/auth",
            state="state",
            expires_at=now,
        )

        assert response.requested_scopes == []


class TestOAuthCallbackRequest:
    """Test OAuthCallbackRequest schema."""

    def test_oauth_callback_request_creation(self):
        """Test creating OAuth callback request."""
        request = OAuthCallbackRequest(
            code="auth-code-123",
            state="state-string",
            error=None,
            error_description=None,
        )

        assert request.code == "auth-code-123"
        assert request.state == "state-string"
        assert request.error is None
        assert request.error_description is None

    def test_oauth_callback_request_with_error(self):
        """Test OAuth callback request with error."""
        request = OAuthCallbackRequest(
            code="dummy-code",
            state="state-string",
            error="access_denied",
            error_description="User denied access",
        )

        assert request.error == "access_denied"
        assert request.error_description == "User denied access"

    def test_oauth_callback_request_validation(self):
        """Test OAuth callback request validation."""
        # Empty code
        with pytest.raises(ValidationError) as exc_info:
            OAuthCallbackRequest(code="", state="state")
        assert "Authorization code cannot be empty" in str(exc_info.value)

        # Empty state
        with pytest.raises(ValidationError) as exc_info:
            OAuthCallbackRequest(code="code", state="")
        assert "OAuth state cannot be empty" in str(exc_info.value)

        # Whitespace trimming
        request = OAuthCallbackRequest(
            code="  auth-code  ",
            state="  state-string  ",
        )
        assert request.code == "auth-code"
        assert request.state == "state-string"


class TestOAuthCallbackResponse:
    """Test OAuthCallbackResponse schema."""

    def test_oauth_callback_response_success(self):
        """Test successful OAuth callback response."""
        response = OAuthCallbackResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            scopes=["email", "profile"],
            external_user_info={"id": "google123", "email": "user@gmail.com"},
            error=None,
        )

        assert response.success is True
        assert response.integration_id == 123
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.status == IntegrationStatus.ACTIVE
        assert response.scopes == ["email", "profile"]
        assert response.external_user_info["id"] == "google123"
        assert response.error is None

    def test_oauth_callback_response_failure(self):
        """Test failed OAuth callback response."""
        response = OAuthCallbackResponse(
            success=False,
            integration_id=None,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ERROR,
            error="Invalid authorization code",
        )

        assert response.success is False
        assert response.integration_id is None
        assert response.status == IntegrationStatus.ERROR
        assert response.error == "Invalid authorization code"
        assert response.scopes == []
        assert response.external_user_info is None


class TestIntegrationUpdateRequest:
    """Test IntegrationUpdateRequest schema."""

    def test_integration_update_request_creation(self):
        """Test creating integration update request."""
        request = IntegrationUpdateRequest(
            scopes=["email", "profile", "calendar"],
            enabled=True,
        )

        assert set(request.scopes) == {"email", "profile", "calendar"}
        assert request.enabled is True

    def test_integration_update_request_defaults(self):
        """Test integration update request defaults."""
        request = IntegrationUpdateRequest()

        assert request.scopes is None
        assert request.enabled is None

    def test_integration_update_request_scope_validation(self):
        """Test scope validation in update request."""
        # Duplicate removal and cleanup
        request = IntegrationUpdateRequest(
            scopes=["email", "profile", "email", "", "calendar"]
        )
        expected_scopes = {"email", "profile", "calendar"}
        assert set(request.scopes) == expected_scopes

        # Empty becomes None
        request = IntegrationUpdateRequest(scopes=["", "  "])
        assert request.scopes is None


class TestTokenRefreshRequest:
    """Test TokenRefreshRequest schema."""

    def test_token_refresh_request_creation(self):
        """Test creating token refresh request."""
        request = TokenRefreshRequest(force=True)
        assert request.force is True

    def test_token_refresh_request_defaults(self):
        """Test token refresh request defaults."""
        request = TokenRefreshRequest()
        assert request.force is False


class TestTokenRefreshResponse:
    """Test TokenRefreshResponse schema."""

    def test_token_refresh_response_success(self):
        """Test successful token refresh response."""
        now = datetime.now(timezone.utc)

        response = TokenRefreshResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            token_expires_at=now,
            refreshed_at=now,
            error=None,
        )

        assert response.success is True
        assert response.integration_id == 123
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.token_expires_at == now
        assert response.refreshed_at == now
        assert response.error is None

    def test_token_refresh_response_failure(self):
        """Test failed token refresh response."""
        now = datetime.now(timezone.utc)

        response = TokenRefreshResponse(
            success=False,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            token_expires_at=None,
            refreshed_at=now,
            error="Refresh token expired",
        )

        assert response.success is False
        assert response.token_expires_at is None
        assert response.error == "Refresh token expired"


class TestIntegrationHealthResponse:
    """Test IntegrationHealthResponse schema."""

    def test_integration_health_response_healthy(self):
        """Test healthy integration response."""
        now = datetime.now(timezone.utc)

        response = IntegrationHealthResponse(
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            healthy=True,
            last_check_at=now,
            issues=[],
            recommendations=[],
        )

        assert response.integration_id == 123
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.status == IntegrationStatus.ACTIVE
        assert response.healthy is True
        assert response.last_check_at == now
        assert response.issues == []
        assert response.recommendations == []

    def test_integration_health_response_unhealthy(self):
        """Test unhealthy integration response."""
        now = datetime.now(timezone.utc)

        response = IntegrationHealthResponse(
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ERROR,
            healthy=False,
            last_check_at=now,
            issues=["Token expired", "API quota exceeded"],
            recommendations=["Refresh tokens", "Contact administrator"],
        )

        assert response.healthy is False
        assert response.issues == ["Token expired", "API quota exceeded"]
        assert response.recommendations == ["Refresh tokens", "Contact administrator"]


class TestIntegrationStatsResponse:
    """Test IntegrationStatsResponse schema."""

    def test_integration_stats_response_creation(self):
        """Test creating integration stats response."""
        response = IntegrationStatsResponse(
            total_integrations=10,
            active_integrations=8,
            failed_integrations=2,
            pending_integrations=0,
            by_provider={"google": 5, "microsoft": 5},
            by_status={"active": 8, "failed": 2},
            recent_errors=[
                {"error": "Token expired", "timestamp": "2023-01-01T00:00:00Z"}
            ],
            sync_stats={"last_sync": "2023-01-01T00:00:00Z", "items_synced": 100},
        )

        assert response.total_integrations == 10
        assert response.active_integrations == 8
        assert response.failed_integrations == 2
        assert response.pending_integrations == 0
        assert response.by_provider == {"google": 5, "microsoft": 5}
        assert response.by_status == {"active": 8, "failed": 2}
        assert len(response.recent_errors) == 1
        assert response.sync_stats["items_synced"] == 100

    def test_integration_stats_response_defaults(self):
        """Test integration stats response defaults."""
        response = IntegrationStatsResponse(
            total_integrations=0,
            active_integrations=0,
            failed_integrations=0,
            pending_integrations=0,
        )

        assert response.by_provider == {}
        assert response.by_status == {}
        assert response.recent_errors == []
        assert response.sync_stats == {}


class TestIntegrationDisconnectRequest:
    """Test IntegrationDisconnectRequest schema."""

    def test_disconnect_request_creation(self):
        """Test creating disconnect request."""
        request = IntegrationDisconnectRequest(
            revoke_tokens=True,
            delete_data=True,
        )

        assert request.revoke_tokens is True
        assert request.delete_data is True

    def test_disconnect_request_defaults(self):
        """Test disconnect request defaults."""
        request = IntegrationDisconnectRequest()

        assert request.revoke_tokens is True
        assert request.delete_data is False


class TestIntegrationDisconnectResponse:
    """Test IntegrationDisconnectResponse schema."""

    def test_disconnect_response_success(self):
        """Test successful disconnect response."""
        now = datetime.now(timezone.utc)

        response = IntegrationDisconnectResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            tokens_revoked=True,
            data_deleted=True,
            disconnected_at=now,
            error=None,
        )

        assert response.success is True
        assert response.integration_id == 123
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.tokens_revoked is True
        assert response.data_deleted is True
        assert response.disconnected_at == now
        assert response.error is None

    def test_disconnect_response_failure(self):
        """Test failed disconnect response."""
        now = datetime.now(timezone.utc)

        response = IntegrationDisconnectResponse(
            success=False,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            tokens_revoked=False,
            data_deleted=False,
            disconnected_at=now,
            error="Failed to revoke tokens",
        )

        assert response.success is False
        assert response.tokens_revoked is False
        assert response.data_deleted is False
        assert response.error == "Failed to revoke tokens"


class TestIntegrationSyncRequest:
    """Test IntegrationSyncRequest schema."""

    def test_sync_request_creation(self):
        """Test creating sync request."""
        request = IntegrationSyncRequest(
            force=True,
            sync_type="full",
        )

        assert request.force is True
        assert request.sync_type == "full"

    def test_sync_request_defaults(self):
        """Test sync request defaults."""
        request = IntegrationSyncRequest()

        assert request.force is False
        assert request.sync_type is None


class TestIntegrationSyncResponse:
    """Test IntegrationSyncResponse schema."""

    def test_sync_response_success(self):
        """Test successful sync response."""
        now = datetime.now(timezone.utc)

        response = IntegrationSyncResponse(
            success=True,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            sync_started_at=now,
            sync_completed_at=now,
            items_synced=50,
            errors=[],
        )

        assert response.success is True
        assert response.integration_id == 123
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.sync_started_at == now
        assert response.sync_completed_at == now
        assert response.items_synced == 50
        assert response.errors == []

    def test_sync_response_with_errors(self):
        """Test sync response with errors."""
        now = datetime.now(timezone.utc)

        response = IntegrationSyncResponse(
            success=False,
            integration_id=123,
            provider=IntegrationProvider.GOOGLE,
            sync_started_at=now,
            sync_completed_at=None,
            items_synced=10,
            errors=["API rate limit exceeded", "Permission denied"],
        )

        assert response.success is False
        assert response.sync_completed_at is None
        assert response.items_synced == 10
        assert response.errors == ["API rate limit exceeded", "Permission denied"]


class TestIntegrationErrorResponse:
    """Test IntegrationErrorResponse schema."""

    def test_error_response_creation(self):
        """Test creating error response."""
        response = IntegrationErrorResponse(
            error="validation_error",
            message="Invalid provider configuration",
            details={"field": "client_id", "issue": "missing"},
            provider=IntegrationProvider.GOOGLE,
            integration_id=123,
        )

        assert response.error == "validation_error"
        assert response.message == "Invalid provider configuration"
        assert response.details == {"field": "client_id", "issue": "missing"}
        assert response.provider == IntegrationProvider.GOOGLE
        assert response.integration_id == 123
        assert isinstance(response.timestamp, datetime)

    def test_error_response_defaults(self):
        """Test error response defaults."""
        response = IntegrationErrorResponse(
            error="generic_error",
            message="Something went wrong",
        )

        assert response.details is None
        assert response.provider is None
        assert response.integration_id is None
        assert isinstance(response.timestamp, datetime)


class TestScopeValidationRequest:
    """Test ScopeValidationRequest schema."""

    def test_scope_validation_request_creation(self):
        """Test creating scope validation request."""
        request = ScopeValidationRequest(
            provider=IntegrationProvider.GOOGLE,
            scopes=["email", "profile", "calendar"],
        )

        assert request.provider == IntegrationProvider.GOOGLE
        assert request.scopes == ["email", "profile", "calendar"]


class TestScopeValidationResponse:
    """Test ScopeValidationResponse schema."""

    def test_scope_validation_response_creation(self):
        """Test creating scope validation response."""
        response = ScopeValidationResponse(
            provider=IntegrationProvider.GOOGLE,
            requested_scopes=["email", "profile", "invalid_scope"],
            valid_scopes=["email", "profile"],
            invalid_scopes=["invalid_scope"],
            warnings=["Sensitive scope requested"],
        )

        assert response.provider == IntegrationProvider.GOOGLE
        assert response.requested_scopes == ["email", "profile", "invalid_scope"]
        assert response.valid_scopes == ["email", "profile"]
        assert response.invalid_scopes == ["invalid_scope"]
        assert response.warnings == ["Sensitive scope requested"]

    def test_scope_validation_response_defaults(self):
        """Test scope validation response defaults."""
        response = ScopeValidationResponse(
            provider=IntegrationProvider.GOOGLE,
            requested_scopes=["email"],
            valid_scopes=["email"],
        )

        assert response.invalid_scopes == []
        assert response.warnings == []


class TestIntegrationListResponse:
    """Test IntegrationListResponse schema."""

    def test_integration_list_response_creation(self):
        """Test creating integration list response."""
        now = datetime.now(timezone.utc)

        integrations = [
            IntegrationResponse(
                id=1,
                user_id="user123",
                provider=IntegrationProvider.GOOGLE,
                status=IntegrationStatus.ACTIVE,
                has_access_token=True,
                has_refresh_token=True,
                created_at=now,
                updated_at=now,
            ),
            IntegrationResponse(
                id=2,
                user_id="user123",
                provider=IntegrationProvider.MICROSOFT,
                status=IntegrationStatus.ERROR,
                has_access_token=False,
                has_refresh_token=False,
                created_at=now,
                updated_at=now,
            ),
        ]

        response = IntegrationListResponse(
            integrations=integrations,
            total=2,
            active_count=1,
            error_count=1,
        )

        assert len(response.integrations) == 2
        assert response.total == 2
        assert response.active_count == 1
        assert response.error_count == 1

    def test_integration_list_response_defaults(self):
        """Test integration list response defaults."""
        response = IntegrationListResponse(
            total=0,
            active_count=0,
            error_count=0,
        )

        assert response.integrations == []


class TestProviderListResponse:
    """Test ProviderListResponse schema."""

    def test_provider_list_response_creation(self):
        """Test creating provider list response."""
        providers = [
            IntegrationProviderInfo(
                name="Google",
                provider=IntegrationProvider.GOOGLE,
                available=True,
            ),
            IntegrationProviderInfo(
                name="Microsoft",
                provider=IntegrationProvider.MICROSOFT,
                available=False,
            ),
        ]

        response = ProviderListResponse(
            providers=providers,
            total=2,
            available_count=1,
        )

        assert len(response.providers) == 2
        assert response.total == 2
        assert response.available_count == 1

    def test_provider_list_response_defaults(self):
        """Test provider list response defaults."""
        response = ProviderListResponse(
            total=0,
            available_count=0,
        )

        assert response.providers == []
