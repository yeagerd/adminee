from unittest.mock import MagicMock, Mock

import pytest
from fastapi import Request

import services.shipments.settings
from services.shipments.service_auth import (
    client_has_permission,
    get_client_permissions,
    service_permission_required,
    verify_service_authentication,
)


@pytest.fixture(autouse=True)
def setup_service_auth():
    """Set up service auth with test API key by patching the settings singleton."""
    test_settings = services.shipments.settings.Settings(
        db_url_shipments="sqlite:///:memory:"
    )
    test_settings.api_frontend_shipments_key = "test-api-key"
    services.shipments.settings._settings = test_settings
    yield
    services.shipments.settings._settings = None


def test_get_client_permissions():
    perms = get_client_permissions("frontend")
    expected = [
        "read_shipments",
        "write_shipments",
        "read_labels",
        "write_labels",
    ]
    assert perms == expected


def test_client_has_permission():
    assert client_has_permission("frontend", "read_shipments") is True
    assert client_has_permission("frontend", "write_labels") is True
    assert client_has_permission("frontend", "not_a_permission") is False
    assert client_has_permission("invalid-client", "read_shipments") is False


@pytest.mark.asyncio
def test_verify_service_authentication_success():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer test-api-key"}
    request.state = Mock()
    service_name = verify_service_authentication(request)
    assert service_name == "shipments-service-access"


@pytest.mark.asyncio
def test_verify_service_authentication_invalid_key():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer invalid-key"}
    request.state = Mock()
    with pytest.raises(Exception):
        verify_service_authentication(request)


@pytest.mark.asyncio
def test_service_permission_required_success():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer test-api-key"}
    request.state = Mock()
    dep = service_permission_required(["read_shipments"])
    service_name = (
        pytest.run(dep(request))
        if hasattr(pytest, "run")
        else pytest.asyncio.run(dep(request))
    )
    assert service_name == "shipments-service-access"


@pytest.mark.asyncio
def test_service_permission_required_failure():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer test-api-key"}
    request.state = Mock()
    dep = service_permission_required(["not_a_permission"])
    with pytest.raises(Exception):
        if hasattr(pytest, "run"):
            pytest.run(dep(request))
        else:
            pytest.asyncio.run(dep(request))
