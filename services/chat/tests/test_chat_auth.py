"""
Tests for Chat Service Authentication.

Tests the API key authentication system for the chat service.
"""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi import Request

from services.chat.auth import (
    API_KEY_CONFIGS,
    service_permission_required,
    verify_service_authentication,
)
from services.chat.settings import get_settings
from services.chat.tests.test_base import BaseChatTest
from services.common.api_key_auth import (
    build_api_key_mapping,
    get_client_from_api_key,
    get_permissions_from_api_key,
    has_permission,
    verify_api_key,
)
from services.common.http_errors import AuthError


class TestChatServiceAuth(BaseChatTest):
    """Test cases for ChatServiceAuth class."""

    def test_chat_service_auth_verify_valid_key(self):
        """Test valid API key verification."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        service_name = verify_api_key("test-frontend-chat-key", api_key_mapping)
        assert service_name == "chat-service-access"

    def test_chat_service_auth_verify_invalid_key(self):
        """Test invalid API key verification."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        service_name = verify_api_key("invalid-key", api_key_mapping)
        assert service_name is None

    def test_chat_service_auth_is_valid_client(self):
        """Test client name validation."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        client_name = get_client_from_api_key("test-frontend-chat-key", api_key_mapping)
        assert client_name == "frontend"

    def test_verify_chat_authentication_success(self):
        """Test successful chat authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        client_name = verify_service_authentication(request)
        assert client_name == "chat-service-access"

    def test_verify_chat_authentication_missing_key(self):
        """Test chat authentication with missing API key."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            verify_service_authentication(request)

        assert exc_info.value.status_code == 401
        assert "API key required" in str(exc_info.value)

    def test_verify_chat_authentication_invalid_key(self):
        """Test chat authentication with invalid API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid-key"}
        request.state = Mock()

        with pytest.raises(AuthError) as exc_info:
            verify_service_authentication(request)

        assert exc_info.value.status_code == 403
        assert "Invalid API key" in str(exc_info.value)

    def test_get_client_permissions_frontend(self):
        """Test getting permissions for frontend client."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        permissions = get_permissions_from_api_key(
            "test-frontend-chat-key", api_key_mapping
        )
        expected = [
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
            "read_feedback",
            "write_feedback",
        ]
        assert permissions == expected

    def test_get_client_permissions_chat(self):
        """Test getting permissions for chat client."""
        # Chat service only has frontend key, so test with invalid key
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        permissions = get_permissions_from_api_key(
            "test-chat-service-key", api_key_mapping
        )
        assert permissions == []

    def test_get_client_permissions_invalid(self):
        """Test getting permissions for invalid client."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        permissions = get_permissions_from_api_key("invalid-key", api_key_mapping)
        assert permissions == []

    def test_client_has_permission_success(self):
        """Test successful client permission check."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        assert (
            has_permission("test-frontend-chat-key", "read_chats", api_key_mapping)
            is True
        )

    def test_client_has_permission_failure(self):
        """Test client permission check failure."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        # Test with invalid key since chat service only has frontend key
        assert (
            has_permission("test-chat-service-key", "write_chats", api_key_mapping)
            is False
        )

    @pytest.mark.asyncio
    async def test_require_chat_auth_success(self):
        """Test require_chat_auth decorator success."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        auth_dep = service_permission_required(["read_chats"])
        client_name = await auth_dep(request)
        assert client_name == "chat-service-access"

    @pytest.mark.asyncio
    async def test_require_chat_auth_restriction_failure(self):
        """Test require_chat_auth decorator with client restriction failure."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-frontend-chat-key"}
        request.state = Mock()

        # Require a permission that frontend doesn't have
        auth_dep = service_permission_required(["admin_access"])
        with pytest.raises(AuthError) as exc_info:
            await auth_dep(request)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in str(exc_info.value)

    def test_require_chat_auth_decorator_factory(self):
        """Test require_chat_auth decorator factory."""
        decorator = service_permission_required(["read_chats"])
        assert callable(decorator)

    def test_multiple_auth_header_formats(self):
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

            client_name = verify_service_authentication(request)
            assert client_name == "chat-service-access"


class TestChatAuthIntegration(BaseChatTest):
    """Integration tests for chat authentication."""

    def test_chat_auth_singleton(self):
        """Test that chat auth instance is a singleton."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        auth1 = get_permissions_from_api_key("test-frontend-chat-key", api_key_mapping)
        auth2 = get_permissions_from_api_key("test-frontend-chat-key", api_key_mapping)
        assert auth1 == auth2

    def test_permission_matrix(self):
        """Test the complete permission matrix for frontend client."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        permissions = get_permissions_from_api_key(
            "test-frontend-chat-key", api_key_mapping
        )

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
            assert (
                has_permission("test-frontend-chat-key", permission, api_key_mapping)
                is True
            )

        assert len(permissions) == len(expected_permissions)

    def test_security_isolation(self):
        """Test that invalid clients have no permissions."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        invalid_keys = ["invalid-key-1", "invalid-key-2", "invalid-key-3"]

        for key in invalid_keys:
            assert get_permissions_from_api_key(key, api_key_mapping) == []
            assert has_permission(key, "read_chats", api_key_mapping) is False
            assert has_permission(key, "write_chats", api_key_mapping) is False
