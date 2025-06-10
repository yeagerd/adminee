"""
Unit tests for authentication modules.

Tests Clerk JWT validation, service authentication, user extraction,
and authorization checks.
"""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from ..auth.clerk import (
    extract_user_id_from_token,
    get_current_user,
    require_user_ownership,
    verify_jwt_token,
    verify_user_ownership,
)
from ..auth.service_auth import (
    ServiceAuthRequired,
    get_current_service,
    require_service_auth,
    service_auth,
    validate_service_permissions,
    verify_service_authentication,
)
from ..exceptions import AuthenticationException, AuthorizationException


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
            patch("services.user_management.auth.clerk.jwt.decode") as mock_decode,
            patch("services.user_management.auth.clerk.settings") as mock_settings,
            patch(
                "services.user_management.auth.clerk.clerk_client"
            ) as mock_clerk_client,
        ):
            mock_settings.clerk_secret_key = "test-secret-key"
            mock_clerk_client.return_value = True  # Just needs to be truthy
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
            patch("services.user_management.auth.clerk.jwt.decode") as mock_decode,
            patch("services.user_management.auth.clerk.settings") as mock_settings,
            patch(
                "services.user_management.auth.clerk.clerk_client"
            ) as mock_clerk_client,
        ):
            mock_settings.clerk_secret_key = "test-secret-key"
            mock_clerk_client.return_value = True  # Just needs to be truthy
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

            with pytest.raises(AuthenticationException) as exc_info:
                await verify_jwt_token("expired_token")

            assert "Token has expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token."""
        with (
            patch("services.user_management.auth.clerk.jwt.decode") as mock_decode,
            patch("services.user_management.auth.clerk.settings") as mock_settings,
            patch(
                "services.user_management.auth.clerk.clerk_client"
            ) as mock_clerk_client,
        ):
            mock_settings.clerk_secret_key = "test-secret-key"
            mock_clerk_client.return_value = True  # Just needs to be truthy
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

            with pytest.raises(AuthenticationException) as exc_info:
                await verify_jwt_token("invalid_token")

            assert "Invalid token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_missing_claims(self):
        """Test JWT token verification with missing required claims."""
        with (
            patch("services.user_management.auth.clerk.jwt.decode") as mock_decode,
            patch("services.user_management.auth.clerk.settings") as mock_settings,
            patch(
                "services.user_management.auth.clerk.clerk_client"
            ) as mock_clerk_client,
        ):
            mock_settings.clerk_secret_key = "test-secret-key"
            mock_clerk_client.return_value = True  # Just needs to be truthy
            mock_decode.return_value = {"sub": "user_123"}  # Missing required claims

            with pytest.raises(AuthenticationException) as exc_info:
                await verify_jwt_token("token")

            assert "Missing required claim: iss" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid_issuer(self):
        """Test JWT token verification with invalid issuer."""
        base_time = 1640995200  # 2022-01-01 00:00:00 UTC
        with (
            patch("services.user_management.auth.clerk.jwt.decode") as mock_decode,
            patch("services.user_management.auth.clerk.settings") as mock_settings,
            patch(
                "services.user_management.auth.clerk.clerk_client"
            ) as mock_clerk_client,
        ):
            mock_settings.clerk_secret_key = "test-secret-key"
            mock_clerk_client.return_value = True  # Just needs to be truthy
            mock_decode.return_value = {
                "sub": "user_123",
                "iss": "https://evil.com",  # Invalid issuer
                "exp": base_time + 3600,
                "iat": base_time,
            }

            with pytest.raises(AuthenticationException) as exc_info:
                await verify_jwt_token("token")

            assert "Invalid token issuer" in str(exc_info.value)

    def test_extract_user_id_from_token_success(self):
        """Test successful user ID extraction from token."""
        claims = {"sub": "user_123", "email": "test@example.com"}
        user_id = extract_user_id_from_token(claims)
        assert user_id == "user_123"

    def test_extract_user_id_from_token_missing(self):
        """Test user ID extraction with missing sub claim."""
        claims = {"email": "test@example.com"}

        with pytest.raises(AuthenticationException) as exc_info:
            extract_user_id_from_token(claims)

        assert "User ID not found in token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful current user extraction."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with patch(
            "services.user_management.auth.clerk.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = {"sub": "user_123"}

            user_id = await get_current_user(credentials)
            assert user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_current_user_auth_failure(self):
        """Test current user extraction with authentication failure."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch(
            "services.user_management.auth.clerk.verify_jwt_token"
        ) as mock_verify:
            mock_verify.side_effect = AuthenticationException("Invalid token")

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
        with pytest.raises(AuthorizationException) as exc_info:
            await verify_user_ownership("user_123", "user_456")

        assert "user_resource:user_456" in exc_info.value.resource
        assert exc_info.value.action == "access"

    @pytest.mark.asyncio
    async def test_require_user_ownership_success(self):
        """Test successful user ownership requirement."""
        with patch(
            "services.user_management.auth.clerk.verify_user_ownership"
        ) as mock_verify:
            mock_verify.return_value = True

            result = await require_user_ownership("user_123", "user_123")
            assert result == "user_123"

    @pytest.mark.asyncio
    async def test_require_user_ownership_failure(self):
        """Test user ownership requirement failure."""
        with patch(
            "services.user_management.auth.clerk.verify_user_ownership"
        ) as mock_verify:
            from ..exceptions import AuthorizationException

            mock_verify.side_effect = AuthorizationException("resource", "action")

            with pytest.raises(HTTPException) as exc_info:
                await require_user_ownership("user_456", "user_123")

            assert exc_info.value.status_code == 403


class TestServiceAuthentication:
    """Test cases for service-to-service authentication."""

    def test_service_api_key_auth_verify_valid_key(self):
        """Test valid API key verification."""
        service_name = service_auth.verify_api_key("dev-service-key")
        assert service_name == "user-management"

    def test_service_api_key_auth_verify_invalid_key(self):
        """Test invalid API key verification."""
        service_name = service_auth.verify_api_key("invalid-key")
        assert service_name is None

    def test_service_api_key_auth_is_valid_service(self):
        """Test service name validation."""
        assert service_auth.is_valid_service("user-management") is True
        assert service_auth.is_valid_service("office-service") is True
        assert service_auth.is_valid_service("invalid-service") is False

    @pytest.mark.asyncio
    async def test_verify_service_authentication_success(self):
        """Test successful service authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer dev-service-key"}

        service_name = await verify_service_authentication(request)
        assert service_name == "user-management"

    @pytest.mark.asyncio
    async def test_verify_service_authentication_missing_key(self):
        """Test service authentication with missing API key."""
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(AuthenticationException) as exc_info:
            await verify_service_authentication(request)

        assert "Service API key required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_service_authentication_invalid_key(self):
        """Test service authentication with invalid API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid-key"}

        with pytest.raises(AuthenticationException) as exc_info:
            await verify_service_authentication(request)

        assert "Invalid service API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_service_success(self):
        """Test successful current service extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Service-Key": "dev-service-key"}

        service_name = await get_current_service(request)
        assert service_name == "user-management"

    @pytest.mark.asyncio
    async def test_get_current_service_auth_failure(self):
        """Test current service extraction with authentication failure."""
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_service(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_service_permissions_success(self):
        """Test successful service permission validation."""
        result = await validate_service_permissions(
            "user-management", ["read_users", "write_users"]
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_service_permissions_failure(self):
        """Test service permission validation failure."""
        result = await validate_service_permissions(
            "chat-service",
            ["write_users"],  # chat-service doesn't have write_users permission
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_service_permissions_no_requirements(self):
        """Test service permission validation with no requirements."""
        result = await validate_service_permissions("chat-service", None)
        assert result is True

    @pytest.mark.asyncio
    async def test_service_auth_required_success(self):
        """Test ServiceAuthRequired dependency success."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer dev-service-key"}

        auth_dep = ServiceAuthRequired(permissions=["read_users"])
        service_name = await auth_dep(request)
        assert service_name == "user-management"

    @pytest.mark.asyncio
    async def test_service_auth_required_permission_failure(self):
        """Test ServiceAuthRequired dependency with permission failure."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer dev-service-key"}

        # user-management service doesn't have "admin" permission
        auth_dep = ServiceAuthRequired(permissions=["admin"])

        with pytest.raises(HTTPException) as exc_info:
            await auth_dep(request)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_service_auth_required_service_restriction(self):
        """Test ServiceAuthRequired dependency with service restriction."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer dev-service-key"}

        # Only allow office-service, but we're authenticating as user-management
        auth_dep = ServiceAuthRequired(allowed_services=["office-service"])

        with pytest.raises(HTTPException) as exc_info:
            await auth_dep(request)

        assert exc_info.value.status_code == 403

    def test_require_service_auth_decorator(self):
        """Test require_service_auth decorator factory."""
        decorator = require_service_auth(allowed_services=["user-management"])
        assert callable(decorator)


class TestAuthenticationIntegration:
    """Integration tests for authentication components."""

    @pytest.mark.asyncio
    async def test_user_and_service_auth_combined(self):
        """Test combining user and service authentication."""
        # This would be used in endpoints that need both user and service auth
        user_id = "user_123"
        service_name = "office-service"

        # Verify user owns resource
        result = await verify_user_ownership(user_id, user_id)
        assert result is True

        # Verify service has permissions
        permissions_valid = await validate_service_permissions(
            service_name, ["read_users"]
        )
        assert permissions_valid is True

    @pytest.mark.asyncio
    async def test_multiple_auth_header_formats(self):
        """Test different authentication header formats."""
        test_cases = [
            {"Authorization": "Bearer dev-service-key"},
            {"X-API-Key": "dev-service-key"},
            {"X-Service-Key": "dev-service-key"},
        ]

        for headers in test_cases:
            request = MagicMock(spec=Request)
            request.headers = headers

            service_name = await verify_service_authentication(request)
            assert service_name == "user-management"
