"""
Unit tests for authentication modules.

Tests Clerk JWT validation, service authentication, user extraction,
and authorization checks.
"""

from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from services.common.http_errors import AuthError
from services.user.auth.nextauth import (
    extract_user_id_from_token,
    get_current_user_flexible,
    require_user_ownership,
    verify_jwt_token,
    verify_user_ownership,
)
from services.user.auth.service_auth import (
    client_has_permission,
    get_client_permissions,
    service_permission_required,
    verify_service_authentication,
)
from services.user.tests.test_base import BaseUserManagementTest


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Patch the _settings global variable to return test settings."""
    import services.user.settings as user_settings

    test_settings = user_settings.Settings(
        db_url_user_management="sqlite:///:memory:",
        api_frontend_user_key="test-frontend-key",
        api_chat_user_key="test-chat-key",
        api_office_user_key="test-office-key",
        api_meetings_user_key="test-meetings-key",
        token_encryption_salt="dGVzdC1zYWx0LTE2Ynl0ZQ==",
        nextauth_jwt_key="test-nextauth-secret",
        oauth_redirect_uri="https://example.com/oauth/callback",
        google_client_id="test-google-client-id",
        google_client_secret="test-google-client-secret",
        azure_ad_client_id="test-microsoft-client-id",
        azure_ad_client_secret="test-microsoft-client-secret",
    )

    monkeypatch.setattr("services.user.settings._settings", test_settings)


class TestNextAuthAuthentication(BaseUserManagementTest):
    """Test cases for NextAuth JWT authentication."""

    def create_test_token(self, claims: Optional[dict] = None, expired: bool = False):
        """Create a test JWT token for testing."""
        # Use fixed timestamps to avoid CI timing issues
        base_time = 1640995200  # 2022-01-01 00:00:00 UTC
        default_claims = {
            "sub": "user_123",
            "iss": "https://nextauth.example.com",
            "iat": base_time,
            "exp": base_time + (3600 if not expired else -3600),
            "email": "test@example.com",
        }

        if claims:
            default_claims.update(claims)

        return jwt.encode(default_claims, "secret", algorithm="HS256")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_success(self):
        """Test successful JWT token verification."""
        token = self.create_test_token()
        base_time = 1640995200  # 2022-01-01 00:00:00 UTC

        with (
            patch("services.user.auth.nextauth.jwt.decode") as mock_decode,
            patch("services.user.auth.nextauth.get_settings") as mock_get_settings,
        ):
            mock_settings = mock_get_settings.return_value
            mock_settings.jwt_verify_signature = False
            mock_decode.return_value = {
                "sub": "user_123",
                "iss": "https://nextauth.example.com",
                "exp": base_time + 3600,
                "iat": base_time,
            }

            result = await verify_jwt_token(token)
            assert result["sub"] == "user_123"
            assert result["iss"] == "https://nextauth.example.com"

    @pytest.mark.asyncio
    async def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token."""
        with (
            patch("services.user.auth.nextauth.jwt.decode") as mock_decode,
            patch("services.user.auth.nextauth.get_settings") as mock_get_settings,
        ):
            mock_settings = mock_get_settings.return_value
            mock_settings.jwt_verify_signature = False
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

            with pytest.raises(AuthError) as exc_info:
                await verify_jwt_token("expired_token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token."""
        with (
            patch("services.user.auth.nextauth.jwt.decode") as mock_decode,
            patch("services.user.auth.nextauth.get_settings") as mock_get_settings,
        ):
            mock_settings = mock_get_settings.return_value
            mock_settings.jwt_verify_signature = False
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

            with pytest.raises(AuthError) as exc_info:
                await verify_jwt_token("invalid_token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_token_missing_claims(self):
        """Test JWT token verification with missing required claims."""
        with (
            patch("services.user.auth.nextauth.jwt.decode") as mock_decode,
            patch("services.user.auth.nextauth.get_settings") as mock_get_settings,
        ):
            mock_settings = mock_get_settings.return_value
            mock_settings.jwt_verify_signature = False
            mock_decode.return_value = {"sub": "user_123"}  # Missing required claims

            with pytest.raises(AuthError) as exc_info:
                await verify_jwt_token("token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid_issuer(self):
        """Test JWT token verification with invalid issuer."""
        base_time = 1640995200  # 2022-01-01 00:00:00 UTC
        with (
            patch("services.user.auth.nextauth.jwt.decode") as mock_decode,
            patch("services.user.auth.nextauth.get_settings") as mock_get_settings,
        ):
            mock_settings = mock_get_settings.return_value
            mock_settings.jwt_verify_signature = False
            mock_decode.return_value = {
                "sub": "user_123",
                "iss": "https://demo.example.com",  # Demo issuer (now allowed)
                "exp": base_time + 3600,
                "iat": base_time,
            }

            # This should now pass since we removed strict issuer validation for demo purposes
            result = await verify_jwt_token("token")
            assert result["sub"] == "user_123"
            assert result["iss"] == "https://demo.example.com"

    def test_extract_user_id_from_token_success(self):
        """Test successful user ID extraction from token."""
        claims = {"sub": "user_123", "email": "test@example.com"}
        user_id = extract_user_id_from_token(claims)
        assert user_id == "user_123"

    def test_extract_user_id_from_token_missing(self):
        """Test user ID extraction with missing sub claim."""
        claims = {"email": "test@example.com"}  # Still a dict, not None

        with pytest.raises(AuthError) as exc_info:
            extract_user_id_from_token(claims)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful current user extraction."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        request = MagicMock(spec=Request)
        request.headers = {}

        with patch("services.user.auth.nextauth.verify_jwt_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123"}

            user_id = await get_current_user_flexible(request, credentials)
            assert user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_current_user_auth_failure(self):
        """Test current user extraction with authentication failure."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )
        request = MagicMock(spec=Request)
        request.headers = {}

        with patch("services.user.auth.nextauth.verify_jwt_token") as mock_verify:
            mock_verify.side_effect = AuthError("Invalid token")

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_flexible(request, credentials)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_user_ownership_success(self):
        """Test successful user ownership verification."""
        result = await verify_user_ownership("user_123", "user_123")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_user_ownership_failure(self):
        """Test user ownership verification failure."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_user_ownership("user_123", "user_456")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_user_ownership_success(self):
        """Test successful user ownership requirement."""
        with patch("services.user.auth.nextauth.verify_user_ownership") as mock_verify:
            mock_verify.return_value = True

            result = await require_user_ownership("user_123", "user_123")
            assert result == "user_123"

    @pytest.mark.asyncio
    async def test_require_user_ownership_failure(self):
        """Test user ownership requirement failure."""
        with patch("services.user.auth.nextauth.verify_user_ownership") as mock_verify:
            mock_verify.side_effect = HTTPException(
                status_code=403, detail="Authorization failed"
            )

            with pytest.raises(HTTPException) as exc_info:
                await require_user_ownership("user_123", "user_456")

            assert exc_info.value.status_code == 403


class TestServiceAuthentication(BaseUserManagementTest):
    """Test cases for service-to-service authentication."""

    def test_user_management_api_key_auth_verify_valid_key(self):
        """Test valid API key verification."""
        perms = get_client_permissions("frontend")
        expected = [
            "read_users",
            "write_users",
            "read_tokens",
            "write_tokens",
            "read_preferences",
            "write_preferences",
        ]
        assert perms == expected

    def test_user_management_api_key_auth_verify_invalid_key(self):
        """Test invalid API key verification."""
        perms = get_client_permissions("invalid-client")
        assert perms == []

    def test_user_management_api_key_auth_is_valid_client(self):
        """Test client name validation."""
        assert client_has_permission("frontend", "read_users") is True
        assert client_has_permission("invalid-client", "read_users") is False

    @pytest.mark.asyncio
    async def test_verify_service_authentication_success(self):
        """Test successful service authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-key"}
        request.state = Mock()

        service_name = verify_service_authentication(request)
        assert service_name == "user-management-access"

    @pytest.mark.asyncio
    async def test_verify_service_authentication_missing_key(self):
        """Test service authentication with missing API key."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            verify_service_authentication(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_service_authentication_invalid_key(self):
        """Test service authentication with invalid API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid-key"}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            verify_service_authentication(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_current_service_success(self):
        """Test successful current service extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Service-Key": "test-frontend-key"}
        request.state = Mock()

        service_name = verify_service_authentication(request)
        assert service_name == "user-management-access"

    @pytest.mark.asyncio
    async def test_get_current_service_auth_failure(self):
        """Test current service extraction with authentication failure."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            verify_service_authentication(request)
        assert exc_info.value.status_code == 401

    def test_get_client_permissions_frontend(self):
        """Test getting permissions for frontend client."""
        permissions = get_client_permissions("frontend")
        expected_permissions = [
            "read_users",
            "write_users",
            "read_tokens",
            "write_tokens",
            "read_preferences",
            "write_preferences",
        ]
        assert permissions == expected_permissions

    def test_get_client_permissions_chat(self):
        """Test getting permissions for chat client."""
        permissions = get_client_permissions("chat")
        expected_permissions = ["read_users", "read_preferences"]
        assert permissions == expected_permissions

    def test_get_client_permissions_office(self):
        """Test getting permissions for office client."""
        permissions = get_client_permissions("office")
        expected_permissions = ["read_users", "read_tokens", "write_tokens"]
        assert permissions == expected_permissions

    def test_get_client_permissions_invalid(self):
        """Test getting permissions for invalid client."""
        permissions = get_client_permissions("invalid-client")
        assert permissions == []

    def test_client_has_permission_success(self):
        """Test successful client permission check."""
        assert client_has_permission("frontend", "read_users") is True
        assert client_has_permission("chat", "read_preferences") is True
        assert client_has_permission("office", "write_tokens") is True

    def test_client_has_permission_failure(self):
        """Test client permission check failure."""
        assert client_has_permission("chat", "write_users") is False
        assert client_has_permission("office", "write_preferences") is False
        assert client_has_permission("invalid-client", "read_users") is False

    @pytest.mark.asyncio
    async def test_require_service_auth_success(self):
        """Test require_service_auth decorator success."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-key"}
        request.state = Mock()

        auth_dep = service_permission_required(["read_users"])
        service_name = await auth_dep(request)
        assert service_name == "user-management-access"

    @pytest.mark.asyncio
    async def test_require_service_auth_restriction_failure(self):
        """Test require_service_auth decorator with client restriction failure."""
        from services.user.auth import service_auth

        # Temporarily modify the API key config to restrict permissions
        original_config = service_auth.API_KEY_CONFIGS["api_frontend_user_key"]
        service_auth.API_KEY_CONFIGS["api_frontend_user_key"] = (
            service_auth.APIKeyConfig(
                client="frontend",
                service="user-management-access",
                permissions=["read_users"],  # Only read_users, not write_tokens
                settings_key="api_frontend_user_key",
            )
        )

        try:
            request = MagicMock(spec=Request)
            request.headers = {"Authorization": "Bearer test-frontend-key"}
            request.state = Mock()
            auth_dep = service_permission_required(["write_tokens"])
            with pytest.raises(AuthError) as exc_info:
                await auth_dep(request)
            assert exc_info.value.status_code == 403
        finally:
            # Restore original config
            service_auth.API_KEY_CONFIGS["api_frontend_user_key"] = original_config

    def test_require_service_auth_decorator_factory(self):
        """Test require_service_auth decorator factory."""
        decorator = service_permission_required(["read_users"])
        assert callable(decorator)


class TestAuthenticationIntegration(BaseUserManagementTest):
    """Integration tests for authentication components."""

    @pytest.mark.asyncio
    async def test_user_and_service_auth_combined(self):
        """Test combining user and service authentication."""
        # This would be used in endpoints that need both user and service auth
        user_id = "user_123"

        # Verify user owns resource
        result = await verify_user_ownership(user_id, user_id)
        assert result is True

        # Verify client has permissions
        assert client_has_permission("office", "read_users") is True
        assert client_has_permission("chat", "read_users") is True
        assert client_has_permission("frontend", "write_users") is True

    @pytest.mark.asyncio
    async def test_multiple_auth_header_formats(self):
        """Test different authentication header formats."""
        test_cases = [
            {"Authorization": "Bearer test-frontend-key"},
            {"X-API-Key": "test-frontend-key"},
            {"X-Service-Key": "test-frontend-key"},
        ]
        for headers in test_cases:
            request = MagicMock(spec=Request)
            request.headers = headers
            request.state = Mock()
            service_name = verify_service_authentication(request)
            assert service_name == "user-management-access"


class TestNextAuthSecurity(BaseUserManagementTest):
    """Test NextAuth security features."""

    @pytest.mark.asyncio
    async def test_jwt_signature_verification_required(self):
        """Test that signature verification fails when required but no secret configured."""
        valid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsImlzcyI6Im5leHRhdXRoIiwiZXhwIjowLCJpYXQiOjB9.dGVzdC1zaWduYXR1cmU="

        with patch("services.user.auth.nextauth.get_settings") as mock_get_settings:
            # Create a mock settings object
            mock_settings = Mock()
            mock_settings.jwt_verify_signature = True
            mock_settings.nextauth_jwt_key = None
            mock_settings.nextauth_issuer = "nextauth"
            mock_settings.nextauth_audience = None
            mock_get_settings.return_value = mock_settings

            with pytest.raises(AuthError, match="JWT verification configuration error"):
                await verify_jwt_token(valid_token)

    @pytest.mark.asyncio
    async def test_jwt_signature_verification_disabled(self):
        """Test that JWT decoding works when signature verification is disabled."""
        with patch("services.user.auth.nextauth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_verify_signature = False
            mock_settings.return_value.nextauth_jwt_key = None

            with patch("services.user.auth.nextauth.jwt.decode") as mock_decode:
                base_time = 1640995200  # 2022-01-01 00:00:00 UTC
                mock_decode.return_value = {
                    "sub": "user_123",
                    "iss": "nextauth",
                    "exp": base_time + 3600,
                    "iat": base_time,
                    "email": "test@example.com",
                }

                result = await verify_jwt_token("test-token")
                assert result["sub"] == "user_123"
                assert result["iss"] == "nextauth"

    @pytest.mark.asyncio
    async def test_jwt_audience_validation(self):
        """Test JWT audience validation when configured."""
        with patch("services.user.auth.nextauth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_verify_signature = True
            mock_settings.return_value.nextauth_jwt_key = "test-secret"
            mock_settings.return_value.nextauth_issuer = "nextauth"
            mock_settings.return_value.nextauth_audience = "briefly-backend"

            with patch("services.user.auth.nextauth.jwt.decode") as mock_decode:
                base_time = 1640995200  # 2022-01-01 00:00:00 UTC
                mock_decode.return_value = {
                    "sub": "user_123",
                    "iss": "nextauth",
                    "aud": "briefly-backend",
                    "exp": base_time + 3600,
                    "iat": base_time,
                    "email": "test@example.com",
                }

                result = await verify_jwt_token("test-token")
                assert result["sub"] == "user_123"
                assert result["aud"] == "briefly-backend"

    @pytest.mark.asyncio
    async def test_jwt_invalid_audience(self):
        """Test that JWT with invalid audience is rejected."""
        with patch("services.user.auth.nextauth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_verify_signature = True
            mock_settings.return_value.nextauth_jwt_key = "test-secret"
            mock_settings.return_value.nextauth_issuer = "nextauth"
            mock_settings.return_value.nextauth_audience = "briefly-backend"

            with patch("services.user.auth.nextauth.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.InvalidAudienceError("Invalid audience")

                with pytest.raises(AuthError, match="Invalid token"):
                    await verify_jwt_token("test-token")

    @pytest.mark.asyncio
    async def test_jwt_invalid_issuer(self):
        """Test that JWT with invalid issuer is rejected."""
        with patch("services.user.auth.nextauth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_verify_signature = True
            mock_settings.return_value.nextauth_jwt_key = "test-secret"
            mock_settings.return_value.nextauth_issuer = "nextauth"
            mock_settings.return_value.nextauth_audience = None

            with patch("services.user.auth.nextauth.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.InvalidIssuerError("Invalid issuer")

                with pytest.raises(AuthError, match="Invalid token"):
                    await verify_jwt_token("test-token")

    @pytest.mark.asyncio
    async def test_jwt_default_audience_validation(self):
        """Test JWT validation with default audience configuration."""
        with patch("services.user.auth.nextauth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_verify_signature = False
            mock_settings.return_value.nextauth_jwt_key = None
            mock_settings.return_value.nextauth_issuer = "nextauth"
            mock_settings.return_value.nextauth_audience = (
                "briefly-backend"  # Default value
            )

            with patch("services.user.auth.nextauth.jwt.decode") as mock_decode:
                base_time = 1640995200  # 2022-01-01 00:00:00 UTC
                mock_decode.return_value = {
                    "sub": "user_123",
                    "iss": "nextauth",
                    "aud": "briefly-backend",  # Matching audience
                    "exp": base_time + 3600,
                    "iat": base_time,
                    "email": "test@example.com",
                }

                result = await verify_jwt_token("test-token")
                assert result["sub"] == "user_123"
                assert result["aud"] == "briefly-backend"
