import asyncio
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import Request


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Patch the get_settings function to return test settings."""
    import services.office.core.settings as office_settings

    def _test_settings():
        return office_settings.Settings(
            db_url_office="sqlite:///:memory:",
            api_frontend_office_key="test-FRONTEND_OFFICE_KEY",
            api_chat_office_key="test-CHAT_OFFICE_KEY",
        )

    monkeypatch.setattr("services.office.core.settings.get_settings", _test_settings)


class TestServiceAuth:
    def test_get_client_permissions(self):
        from services.office.core.auth import get_test_api_keys

        api_keys = get_test_api_keys()
        assert "frontend" in api_keys
        assert "chat" in api_keys
        assert api_keys["frontend"] == "test-FRONTEND_OFFICE_KEY"
        assert api_keys["chat"] == "test-CHAT_OFFICE_KEY"

    def test_verify_api_key_for_testing(self):
        from services.office.core.auth import verify_api_key_for_testing

        # Test with valid frontend key
        result = verify_api_key_for_testing("test-FRONTEND_OFFICE_KEY")
        assert result == "office-service-access"

        # Test with valid chat key
        result = verify_api_key_for_testing("test-CHAT_OFFICE_KEY")
        assert result == "office-service-access"

        # Test with invalid key
        result = verify_api_key_for_testing("invalid-key")
        assert result is None

    def test_verify_service_authentication_success(self):
        from services.office.core.auth import verify_service_authentication

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-FRONTEND_OFFICE_KEY"}
        request.state = Mock()
        service_name = verify_service_authentication(request)
        assert service_name == "office-service-access"

    def test_verify_service_authentication_invalid_key(self):
        from services.office.core.auth import verify_service_authentication

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid-key"}
        request.state = Mock()
        with pytest.raises(Exception):
            verify_service_authentication(request)

    def test_service_permission_required_success(self):
        from services.office.core.auth import service_permission_required

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-FRONTEND_OFFICE_KEY"}
        request.state = Mock()
        dep = service_permission_required(["read_emails"])
        service_name = asyncio.run(dep(request))
        assert service_name == "office-service-access"

    def test_service_permission_required_failure(self):
        from services.office.core.auth import service_permission_required

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-FRONTEND_OFFICE_KEY"}
        request.state = Mock()
        dep = service_permission_required(["not_a_permission"])
        with pytest.raises(Exception):
            asyncio.run(dep(request))

    def test_optional_service_auth_success(self):
        from services.office.core.auth import optional_service_auth

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-FRONTEND_OFFICE_KEY"}
        request.state = Mock()
        service_name = optional_service_auth(request)
        assert service_name == "office-service-access"

    def test_optional_service_auth_failure(self):
        from services.office.core.auth import optional_service_auth

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid-key"}
        request.state = Mock()
        service_name = optional_service_auth(request)
        assert service_name is None
