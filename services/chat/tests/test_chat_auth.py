"""
Tests for Chat Service Authentication.

Tests the API key authentication system for the chat service.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import Request

from services.chat.auth import (
    client_has_permission,
    get_chat_auth,
    get_client_permissions,
    require_chat_auth,
    verify_chat_authentication,
)
from services.common.http_errors import AuthError


class TestChatServiceAuth:
    """Test cases for ChatServiceAuth class."""

    @pytest.fixture(autouse=True)
    def setup_chat_auth_for_service_tests(self):
        """Set up chat auth with test API key."""
        with patch("services.chat.auth.get_settings") as mock_settings:
            mock_settings.return_value.api_frontend_chat_key = "test-frontend-chat-key"

            # Reset the global chat auth instance
            import services.chat.auth as auth_module

            auth_module._chat_auth = None
            yield

    def test_chat_service_auth_verify_valid_key(self):
        """Test valid API key verification."""
        client_name = get_chat_auth().verify_api_key_value("test-frontend-chat-key")
        assert client_name == "frontend"

    def test_chat_service_auth_verify_invalid_key(self):
        """Test invalid API key verification."""
        client_name = get_chat_auth().verify_api_key_value("invalid-key")
        assert client_name is None

    def test_chat_service_auth_is_valid_client(self):
        """Test client name validation."""
        assert get_chat_auth().is_valid_client("frontend") is True
        assert get_chat_auth().is_valid_client("invalid-client") is False

    @pytest.mark.asyncio
    async def test_verify_chat_authentication_success(self):
        """Test successful chat authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        client_name = await verify_chat_authentication(request)
        assert client_name == "frontend"

    @pytest.mark.asyncio
    async def test_verify_chat_authentication_missing_key(self):
        """Test chat authentication with missing API key."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            await verify_chat_authentication(request)

        assert exc_info.value.status_code == 401
        assert "API key required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_chat_authentication_invalid_key(self):
        """Test chat authentication with invalid API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid-key"}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            await verify_chat_authentication(request)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)

    def test_get_client_permissions_frontend(self):
        """Test getting permissions for frontend client."""
        permissions = get_client_permissions("frontend")
        expected_permissions = [
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
            "read_feedback",
            "write_feedback",
        ]
        assert permissions == expected_permissions

    def test_get_client_permissions_invalid(self):
        """Test getting permissions for invalid client."""
        permissions = get_client_permissions("invalid-client")
        assert permissions == []

    def test_client_has_permission_success(self):
        """Test successful client permission check."""
        assert client_has_permission("frontend", "read_chats") is True
        assert client_has_permission("frontend", "write_chats") is True
        assert client_has_permission("frontend", "read_threads") is True

    def test_client_has_permission_failure(self):
        """Test client permission check failure."""
        assert client_has_permission("invalid-client", "read_chats") is False
        assert client_has_permission("frontend", "invalid_permission") is False

    @pytest.mark.asyncio
    async def test_require_chat_auth_success(self):
        """Test require_chat_auth decorator success."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        auth_dep = require_chat_auth(allowed_clients=["frontend"])
        client_name = await auth_dep(request)
        assert client_name == "frontend"

    @pytest.mark.asyncio
    async def test_require_chat_auth_restriction_failure(self):
        """Test require_chat_auth decorator with client restriction failure."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        # Only allow invalid client, but we're authenticating as frontend
        auth_dep = require_chat_auth(allowed_clients=["invalid-client"])

        with pytest.raises(AuthError) as exc_info:
            await auth_dep(request)

        assert exc_info.value.status_code == 403
        assert "not authorized" in str(exc_info.value).lower()

    def test_require_chat_auth_decorator_factory(self):
        """Test require_chat_auth decorator factory."""
        decorator = require_chat_auth(allowed_clients=["frontend"])
        assert callable(decorator)

    @pytest.mark.asyncio
    async def test_multiple_auth_header_formats(self):
        """Test different authentication header formats."""
        test_cases = [
            {"Authorization": "Bearer test-frontend-chat-key"},
            {"X-API-Key": "test-frontend-chat-key"},
            {"X-Service-Key": "test-frontend-chat-key"},
        ]

        for headers in test_cases:
            request = MagicMock(spec=Request)
            request.headers = headers
            request.state = Mock()

            client_name = await verify_chat_authentication(request)
            assert client_name == "frontend"


class TestChatAuthIntegration:
    """Integration tests for chat authentication."""

    @pytest.fixture(autouse=True)
    def setup_chat_auth_for_integration_tests(self):
        """Set up chat auth with test API key."""
        with patch("services.chat.auth.get_settings") as mock_settings:
            mock_settings.return_value.api_frontend_chat_key = "test-frontend-chat-key"

            # Reset the global chat auth instance
            import services.chat.auth as auth_module

            auth_module._chat_auth = None
            yield

    def test_chat_auth_singleton(self):
        """Test that chat auth instance is a singleton."""
        auth1 = get_chat_auth()
        auth2 = get_chat_auth()
        assert auth1 is auth2

    def test_permission_matrix(self):
        """Test the complete permission matrix for frontend client."""
        permissions = get_client_permissions("frontend")

        # Verify all expected permissions exist
        expected_permissions = [
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
            "read_feedback",
            "write_feedback",
        ]

        for permission in expected_permissions:
            assert permission in permissions
            assert client_has_permission("frontend", permission) is True

        assert len(permissions) == len(expected_permissions)

    def test_security_isolation(self):
        """Test that invalid clients have no permissions."""
        invalid_clients = ["chat", "office", "admin", "invalid"]

        for client in invalid_clients:
            assert get_client_permissions(client) == []
            assert client_has_permission(client, "read_chats") is False
            assert client_has_permission(client, "write_chats") is False
