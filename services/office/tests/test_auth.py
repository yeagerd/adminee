"""
Tests for office service authentication and authorization system.

Tests the granular API key authentication and permission system for the office service,
including API key validation, permission checking, and service authentication dependencies.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from services.office.core.auth import (
    ServicePermissionRequired,
    get_api_key_from_request,
    get_client_from_api_key,
    get_permissions_from_api_key,
    has_permission,
    optional_service_auth,
    validate_service_permissions,
    verify_api_key,
    verify_service_authentication,
)
from services.office.core.settings import get_settings


# Test settings fixture
@pytest.fixture(scope="session")
def test_settings():
    """Get settings for testing."""
    return get_settings()


# Helper function to get API key values
def get_test_api_keys():
    """Get the actual API key values from settings for testing."""
    settings = get_settings()
    return {
        "frontend": settings.api_frontend_office_key,
        "chat": settings.api_chat_office_key,
    }


class TestAPIKeyFunctions:
    """Test the core API key utility functions."""

    def test_verify_api_key_valid_frontend_key(self):
        """Test valid frontend API key verification."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        service_name = verify_api_key(settings.api_frontend_office_key)
        assert service_name == "office-service-access"

    def test_verify_api_key_valid_chat_key(self):
        """Test valid chat service API key verification."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        service_name = verify_api_key(settings.api_chat_office_key)
        assert service_name == "office-service-access"

    def test_verify_api_key_invalid_key(self):
        """Test invalid API key verification."""
        service_name = verify_api_key("invalid-key")
        assert service_name is None

    def test_verify_api_key_empty_key(self):
        """Test empty API key verification."""
        service_name = verify_api_key("")
        assert service_name is None

    def test_verify_api_key_none_key(self):
        """Test None API key verification."""
        service_name = verify_api_key(None)
        assert service_name is None

    def test_get_client_from_api_key_frontend(self):
        """Test getting client name from frontend API key."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        client = get_client_from_api_key(settings.api_frontend_office_key)
        assert client == "frontend"

    def test_get_client_from_api_key_chat_service(self):
        """Test getting client name from chat service API key."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        client = get_client_from_api_key(settings.api_chat_office_key)
        assert client == "chat-service"

    def test_get_client_from_api_key_invalid(self):
        """Test getting client name from invalid API key."""
        client = get_client_from_api_key("invalid-key")
        assert client is None

    def test_get_permissions_from_api_key_frontend(self):
        """Test getting permissions from frontend API key."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        permissions = get_permissions_from_api_key(settings.api_frontend_office_key)
        expected = [
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
        ]
        assert permissions == expected

    def test_get_permissions_from_api_key_chat_service(self):
        """Test getting permissions from chat service API key."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        permissions = get_permissions_from_api_key(settings.api_chat_office_key)
        expected = ["read_emails", "read_calendar", "read_files"]
        assert permissions == expected

    def test_get_permissions_from_api_key_invalid(self):
        """Test getting permissions from invalid API key."""
        permissions = get_permissions_from_api_key("invalid-key")
        assert permissions == []

    def test_has_permission_frontend_send_emails(self):
        """Test frontend has send_emails permission."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        result = has_permission(settings.api_frontend_office_key, "send_emails")
        assert result is True

    def test_has_permission_chat_service_no_send_emails(self):
        """Test chat service does not have send_emails permission."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        result = has_permission(settings.api_chat_office_key, "send_emails")
        assert result is False

    def test_has_permission_chat_service_read_emails(self):
        """Test chat service has read_emails permission."""
        from services.office.core.settings import get_settings

        settings = get_settings()
        result = has_permission(settings.api_chat_office_key, "read_emails")
        assert result is True

    def test_has_permission_invalid_key(self):
        """Test permission check with invalid API key."""
        result = has_permission("invalid-key", "read_emails")
        assert result is False


class TestServicePermissionValidation:
    """Test service permission validation logic."""

    @pytest.mark.asyncio
    async def test_validate_service_permissions_with_api_key_success(self):
        """Test successful permission validation with API key."""
        api_keys = get_test_api_keys()
        result = await validate_service_permissions(
            "office-service-access",
            ["read_emails", "send_emails"],
            api_keys["frontend"],
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_service_permissions_with_api_key_failure(self):
        """Test failed permission validation with API key."""
        api_keys = get_test_api_keys()
        result = await validate_service_permissions(
            "office-service-access",
            ["send_emails"],
            api_keys["chat"],  # Chat service can't send emails
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_service_permissions_no_requirements(self):
        """Test permission validation with no requirements."""
        api_keys = get_test_api_keys()
        result = await validate_service_permissions(
            "office-service-access", None, api_keys["chat"]
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_service_permissions_empty_requirements(self):
        """Test permission validation with empty requirements."""
        api_keys = get_test_api_keys()
        result = await validate_service_permissions(
            "office-service-access", [], api_keys["chat"]
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_service_permissions_fallback_service_level(self):
        """Test permission validation fallback to service level."""
        result = await validate_service_permissions(
            "office-service-access",
            ["read_emails"],
            None,  # No API key, use service-level fallback
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_service_permissions_fallback_invalid_permission(self):
        """Test permission validation fallback with invalid permission."""
        result = await validate_service_permissions(
            "office-service-access", ["invalid_permission"], None
        )
        assert result is False


class TestAPIKeyExtraction:
    """Test API key extraction from requests."""

    @pytest.mark.asyncio
    async def test_get_api_key_from_x_api_key_header(self):
        """Test API key extraction from X-API-Key header."""
        request = Mock()
        request.headers = {"X-API-Key": "test-api-key"}

        api_key = await get_api_key_from_request(request)
        assert api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_api_key_from_authorization_header(self):
        """Test API key extraction from Authorization Bearer header."""
        request = Mock()
        request.headers = {"Authorization": "Bearer test-api-key"}

        api_key = await get_api_key_from_request(request)
        assert api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_api_key_from_service_key_header(self):
        """Test API key extraction from X-Service-Key header."""
        request = Mock()
        request.headers = {"X-Service-Key": "test-api-key"}

        api_key = await get_api_key_from_request(request)
        assert api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_api_key_preference_x_api_key(self):
        """Test that X-API-Key header takes preference."""
        request = Mock()
        request.headers = {
            "X-API-Key": "preferred-key",
            "Authorization": "Bearer other-key",
            "X-Service-Key": "another-key",
        }

        api_key = await get_api_key_from_request(request)
        assert api_key == "preferred-key"

    @pytest.mark.asyncio
    async def test_get_api_key_no_headers(self):
        """Test API key extraction with no relevant headers."""
        request = Mock()
        request.headers = {}

        api_key = await get_api_key_from_request(request)
        assert api_key is None

    @pytest.mark.asyncio
    async def test_get_api_key_invalid_authorization_format(self):
        """Test API key extraction with invalid Authorization format."""
        request = Mock()
        request.headers = {"Authorization": "Basic invalid-format"}

        api_key = await get_api_key_from_request(request)
        assert api_key is None


class TestServiceAuthentication:
    """Test service authentication workflow."""

    @pytest.mark.asyncio
    async def test_verify_service_authentication_success(self):
        """Test successful service authentication."""
        request = Mock()
        request.headers = {"X-API-Key": get_test_api_keys()["frontend"]}
        request.state = Mock()

        service_name = await verify_service_authentication(request)
        assert service_name == "office-service-access"
        assert request.state.api_key == get_test_api_keys()["frontend"]
        assert request.state.service_name == "office-service-access"
        assert request.state.client_name == "frontend"

    @pytest.mark.asyncio
    async def test_verify_service_authentication_missing_api_key(self):
        """Test service authentication with missing API key."""
        request = Mock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await verify_service_authentication(request)

        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_service_authentication_invalid_api_key(self):
        """Test service authentication with invalid API key."""
        request = Mock()
        request.headers = {"X-API-Key": "invalid-key"}

        with pytest.raises(HTTPException) as exc_info:
            await verify_service_authentication(request)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_optional_service_auth_success(self):
        """Test optional service authentication success."""
        request = Mock()
        request.headers = {"X-API-Key": get_test_api_keys()["frontend"]}
        request.state = Mock()

        service_name = await optional_service_auth(request)
        assert service_name == "office-service-access"

    @pytest.mark.asyncio
    async def test_optional_service_auth_failure(self):
        """Test optional service authentication failure."""
        request = Mock()
        request.headers = {}

        service_name = await optional_service_auth(request)
        assert service_name is None


class TestServicePermissionRequired:
    """Test the ServicePermissionRequired dependency."""

    @pytest.mark.asyncio
    async def test_service_permission_required_success(self):
        """Test successful permission check."""
        request = Mock()
        request.headers = {"X-API-Key": get_test_api_keys()["frontend"]}
        request.state = Mock()

        permission_check = ServicePermissionRequired(["send_emails"])
        service_name = await permission_check(request)

        assert service_name == "office-service-access"

    @pytest.mark.asyncio
    async def test_service_permission_required_insufficient_permissions(self):
        """Test permission check with insufficient permissions."""
        request = Mock()
        request.headers = {
            "X-API-Key": get_test_api_keys()["chat"]
        }  # Can't send emails
        request.state = Mock()

        permission_check = ServicePermissionRequired(["send_emails"])

        with pytest.raises(HTTPException) as exc_info:
            await permission_check(request)

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_permission_required_multiple_permissions(self):
        """Test permission check with multiple required permissions."""
        request = Mock()
        request.headers = {"X-API-Key": get_test_api_keys()["frontend"]}
        request.state = Mock()

        permission_check = ServicePermissionRequired(["read_emails", "send_emails"])
        service_name = await permission_check(request)

        assert service_name == "office-service-access"

    @pytest.mark.asyncio
    async def test_service_permission_required_missing_api_key_state(self):
        """Test permission check with missing API key in state."""
        # Mock the authentication to pass but not set api_key in state
        request = Mock()
        request.state = Mock()
        request.state.api_key = None  # Missing API key

        permission_check = ServicePermissionRequired(["read_emails"])

        with patch(
            "services.office.core.auth.verify_service_authentication"
        ) as mock_auth:
            mock_auth.return_value = "office-service-access"

            with pytest.raises(HTTPException) as exc_info:
                await permission_check(request)

            assert exc_info.value.status_code == 500
            assert "API key not found in request state" in exc_info.value.detail


class TestIntegrationWithFastAPI:
    """Test integration with FastAPI endpoints."""

    def test_fastapi_integration_send_email_endpoint(self):
        """Test FastAPI integration with send email endpoint."""
        app = FastAPI()

        @app.post("/emails/send")
        async def send_email(
            service_name: str = Depends(ServicePermissionRequired(["send_emails"])),
        ):
            return {"status": "sent", "service": service_name}

        client = TestClient(app)

        # Test with frontend key (should work)
        response = client.post(
            "/emails/send", headers={"X-API-Key": get_test_api_keys()["frontend"]}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "sent"

        # Test with chat service key (should fail)
        response = client.post(
            "/emails/send", headers={"X-API-Key": get_test_api_keys()["chat"]}
        )
        assert response.status_code == 403

    def test_fastapi_integration_read_email_endpoint(self):
        """Test FastAPI integration with read email endpoint."""
        app = FastAPI()

        @app.get("/emails")
        async def get_emails(
            service_name: str = Depends(ServicePermissionRequired(["read_emails"])),
        ):
            return {"emails": [], "service": service_name}

        client = TestClient(app)

        # Test with frontend key (should work)
        response = client.get(
            "/emails", headers={"X-API-Key": get_test_api_keys()["frontend"]}
        )
        assert response.status_code == 200

        # Test with chat service key (should also work)
        response = client.get(
            "/emails", headers={"X-API-Key": get_test_api_keys()["chat"]}
        )
        assert response.status_code == 200

    def test_fastapi_integration_no_api_key(self):
        """Test FastAPI integration with no API key."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(
            service_name: str = Depends(ServicePermissionRequired(["read_emails"])),
        ):
            return {"service": service_name}

        client = TestClient(app)

        response = client.get("/protected")
        assert response.status_code == 401

    def test_fastapi_integration_invalid_api_key(self):
        """Test FastAPI integration with invalid API key."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(
            service_name: str = Depends(ServicePermissionRequired(["read_emails"])),
        ):
            return {"service": service_name}

        client = TestClient(app)

        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401


class TestPermissionMatrix:
    """Test the permission matrix for different API keys."""

    def test_frontend_permissions_complete(self):
        """Test that frontend key has all expected permissions."""
        permissions = get_permissions_from_api_key(get_test_api_keys()["frontend"])
        expected = [
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
        ]

        for permission in expected:
            assert permission in permissions

        assert len(permissions) == len(expected)

    def test_chat_service_permissions_read_only(self):
        """Test that chat service key has only read permissions."""
        permissions = get_permissions_from_api_key(get_test_api_keys()["chat"])

        # Should have read permissions
        assert "read_emails" in permissions
        assert "read_calendar" in permissions
        assert "read_files" in permissions

        # Should NOT have write permissions
        assert "send_emails" not in permissions
        assert "write_calendar" not in permissions
        assert "write_files" not in permissions


class TestSecurityScenarios:
    """Test various security scenarios."""

    def test_email_sending_security(self):
        """Test that only authorized clients can send emails."""
        # Frontend can send
        assert has_permission(get_test_api_keys()["frontend"], "send_emails") is True

        # Chat service cannot send
        assert has_permission(get_test_api_keys()["chat"], "send_emails") is False

    def test_calendar_writing_security(self):
        """Test that only authorized clients can write to calendar."""
        # Frontend can write
        assert has_permission(get_test_api_keys()["frontend"], "write_calendar") is True

        # Chat service cannot write
        assert has_permission(get_test_api_keys()["chat"], "write_calendar") is False

    def test_file_access_security(self):
        """Test file access permissions."""
        # Frontend can read and write
        assert has_permission(get_test_api_keys()["frontend"], "read_files") is True
        assert has_permission(get_test_api_keys()["frontend"], "write_files") is True

        # Chat service can only read
        assert has_permission(get_test_api_keys()["chat"], "read_files") is True
        assert has_permission(get_test_api_keys()["chat"], "write_files") is False

    @pytest.mark.asyncio
    async def test_privilege_escalation_prevention(self):
        """Test that services cannot escalate privileges."""
        # Chat service should not be able to perform write operations
        result = await validate_service_permissions(
            "office-service-access",
            ["send_emails", "write_calendar"],
            get_test_api_keys()["chat"],
        )
        assert result is False

    def test_api_key_enumeration_protection(self):
        """Test protection against API key enumeration."""
        # Various invalid keys should all return None
        invalid_keys = [
            "api-frontend-invalid-key",
            "api-chat-invalid-key",
            "completely-invalid",
            "",
            None,
        ]

        for key in invalid_keys:
            assert verify_api_key(key) is None
            assert get_client_from_api_key(key) is None
            assert get_permissions_from_api_key(key) == []
