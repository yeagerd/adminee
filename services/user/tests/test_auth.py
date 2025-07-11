"""
Unit tests for authentication modules.

Tests Clerk JWT validation, service authentication, user extraction,
and authorization checks.
"""

from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from services.common.http_errors import AuthError

from services.user.auth.nextauth import (
    extract_user_id_from_token,
    get_current_user,
    require_user_ownership,
    verify_jwt_token,
    verify_user_ownership,
)
from services.user.auth.service_auth import (
    client_has_permission,
    get_client_permissions,
    get_current_service,
    get_service_auth,
    require_service_auth,
    verify_service_authentication,
)


class TestClerkAuthentication:
    """Test cases for Clerk JWT authentication."""

    def create_test_token(self, claims: dict = None, expired: bool = False):
        """Create a test JWT token for testing."""
        # Use fixed timestamps to avoid CI timing issues
        base_time = 1640995200  # 2022-01-01 00:00:00 UTC
        default_claims = {
            "sub": "user_123",
            "iss": "https://clerk.example.com",
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
                "iss": "https://clerk.example.com",
                "exp": base_time + 3600,
                "iat": base_time,
            }

            result = await verify_jwt_token(token)
            assert result["sub"] == "user_123"
            assert result["iss"] == "https://clerk.example.com"

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

        with patch("services.user.auth.nextauth.verify_jwt_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123"}

            user_id = await get_current_user(credentials)
            assert user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_current_user_auth_failure(self):
        """Test current user extraction with authentication failure."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch("services.user.auth.nextauth.verify_jwt_token") as mock_verify:
            mock_verify.side_effect = AuthError("Invalid token")

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

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


class TestServiceAuthentication:
    """Test cases for service-to-service authentication."""

    @pytest.fixture(autouse=True)
    def setup_service_auth(self):
        """Set up service auth with test API key."""
        with patch("services.user.auth.service_auth.get_settings") as mock_settings:
            mock_settings.return_value.api_frontend_user_key = "test-frontend-key"
            mock_settings.return_value.api_chat_user_key = "test-chat-key"
            mock_settings.return_value.api_office_user_key = "test-office-key"

            # Reset the global service auth instance
            import services.user.auth.service_auth as auth_module

            auth_module._service_auth = None
            yield

    def test_user_management_api_key_auth_verify_valid_key(self):
        """Test valid API key verification."""
        client_name = get_service_auth().verify_api_key_value("test-frontend-key")
        assert client_name == "frontend"

    def test_user_management_api_key_auth_verify_invalid_key(self):
        """Test invalid API key verification."""
        client_name = get_service_auth().verify_api_key_value("invalid-key")
        assert client_name is None

    def test_user_management_api_key_auth_is_valid_client(self):
        """Test client name validation."""
        assert get_service_auth().is_valid_client("frontend") is True
        assert get_service_auth().is_valid_client("invalid-client") is False

    @pytest.mark.asyncio
    async def test_verify_service_authentication_success(self):
        """Test successful service authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-key"}
        request.state = Mock()

        client_name = await verify_service_authentication(request)
        assert client_name == "frontend"

    @pytest.mark.asyncio
    async def test_verify_service_authentication_missing_key(self):
        """Test service authentication with missing API key."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            await verify_service_authentication(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_service_authentication_invalid_key(self):
        """Test service authentication with invalid API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid-key"}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            await verify_service_authentication(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_service_success(self):
        """Test successful current service extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Service-Key": "test-frontend-key"}
        request.state = Mock()

        client_name = await get_current_service(request)
        assert client_name == "frontend"

    @pytest.mark.asyncio
    async def test_get_current_service_auth_failure(self):
        """Test current service extraction with authentication failure."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            await get_current_service(request)
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

        auth_dep = require_service_auth(allowed_clients=["frontend"])
        client_name = await auth_dep(request)
        assert client_name == "frontend"

    @pytest.mark.asyncio
    async def test_require_service_auth_restriction_failure(self):
        """Test require_service_auth decorator with client restriction failure."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-key"}
        request.state = Mock()

        # Only allow chat client, but we're authenticating as frontend
        auth_dep = require_service_auth(allowed_clients=["chat"])

        with pytest.raises(AuthError) as exc_info:
            await auth_dep(request)
        assert exc_info.value.status_code == 401

    def test_require_service_auth_decorator_factory(self):
        """Test require_service_auth decorator factory."""
        decorator = require_service_auth(allowed_clients=["frontend"])
        assert callable(decorator)


class TestAuthenticationIntegration:
    """Integration tests for authentication components."""

    @pytest.fixture(autouse=True)
    def setup_service_auth(self):
        """Set up service auth with test API key."""
        with patch("services.user.auth.service_auth.get_settings") as mock_settings:
            mock_settings.return_value.api_frontend_user_key = "test-frontend-key"
            mock_settings.return_value.api_chat_user_key = "test-chat-key"
            mock_settings.return_value.api_office_user_key = "test-office-key"

            # Reset the global service auth instance
            import services.user.auth.service_auth as auth_module

            auth_module._service_auth = None
            yield

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

            client_name = await verify_service_authentication(request)
            assert client_name == "frontend"
