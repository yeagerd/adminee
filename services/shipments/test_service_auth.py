import asyncio
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import Request

from services.shipments.test_base import BaseShipmentsTest


class TestServiceAuth(BaseShipmentsTest):
    def test_get_client_permissions(self):
        from services.shipments.service_auth import get_client_permissions

        perms = get_client_permissions("frontend")
        expected = [
            "read_shipments",
            "write_shipments",
            "read_labels",
            "write_labels",
            "parse_emails",
            "collect_data",
        ]
        assert perms == expected

    def test_client_has_permission(self):
        from services.shipments.service_auth import client_has_permission

        assert client_has_permission("frontend", "read_shipments") is True
        assert client_has_permission("frontend", "write_labels") is True
        assert client_has_permission("frontend", "not_a_permission") is False
        assert client_has_permission("invalid-client", "read_shipments") is False

    def test_verify_service_authentication_success(self):
        from services.shipments.service_auth import verify_service_authentication

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-api-key"}
        request.state = Mock()
        service_name = verify_service_authentication(request)
        assert service_name == "shipments-service-access"

    def test_verify_service_authentication_invalid_key(self):
        from services.shipments.service_auth import verify_service_authentication

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid-key"}
        request.state = Mock()
        with pytest.raises(Exception):
            verify_service_authentication(request)

    def test_service_permission_required_success(self):
        from services.shipments.service_auth import service_permission_required

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-api-key"}
        request.state = Mock()
        dep = service_permission_required(["read_shipments"])
        service_name = asyncio.run(dep(request))
        assert service_name == "shipments-service-access"

    def test_service_permission_required_failure(self):
        from services.shipments.service_auth import service_permission_required

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test-api-key"}
        request.state = Mock()
        dep = service_permission_required(["not_a_permission"])
        with pytest.raises(Exception):
            asyncio.run(dep(request))
