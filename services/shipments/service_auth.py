from typing import Any, Callable, Dict, List

from fastapi import Request

from services.common.api_key_auth import (
    APIKeyConfig,
)
from services.common.api_key_auth import (
    client_has_permission as shared_client_has_permission,
)
from services.common.api_key_auth import (
    get_client_permissions as shared_get_client_permissions,
)
from services.common.api_key_auth import (
    make_service_permission_required,
    make_verify_service_authentication,
)
from services.shipments.settings import get_settings

# API Key configurations mapped by settings key names
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    "api_frontend_shipments_key": APIKeyConfig(
        client="frontend",
        service="shipments-service-access",
        permissions=[
            "read_shipments",
            "write_shipments",
            "read_labels",
            "write_labels",
        ],
        settings_key="api_frontend_shipments_key",
    ),
}

# Service-level permissions fallback (optional, for legacy support)
SERVICE_PERMISSIONS = {
    "shipments-service-access": [
        "read_shipments",
        "write_shipments",
        "read_labels",
        "write_labels",
    ],
}

# FastAPI dependencies
verify_service_authentication = make_verify_service_authentication(
    API_KEY_CONFIGS, get_settings
)


def service_permission_required(
    required_permissions: List[str],
) -> Callable[[Request], Any]:
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )


def get_client_permissions(client_name: str) -> list[str]:
    return shared_get_client_permissions(
        client_name,
        {
            "frontend": [
                "read_shipments",
                "write_shipments",
                "read_labels",
                "write_labels",
            ],
        },
    )


def client_has_permission(client_name: str, required_permission: str) -> bool:
    return shared_client_has_permission(
        client_name,
        required_permission,
        {
            "frontend": [
                "read_shipments",
                "write_shipments",
                "read_labels",
                "write_labels",
            ],
        },
    )
