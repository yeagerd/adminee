"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.

**Terminology Clarification:**
- api_key_name: The identifier/name for an API key (e.g., "api-frontend-user-key")
- api_key_value: The actual secret value stored in environment variables (e.g., "test-FRONTEND-123...")
- service_name: The service identifier (e.g., "user-management-access")
"""

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
from services.common.logging_config import get_logger
from services.user.settings import get_settings

logger = get_logger(__name__)

# API Key configurations mapped by settings key names
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    "api_frontend_user_key": APIKeyConfig(
        client="frontend",
        service="user-management-access",
        permissions=[
            "read_users",
            "write_users",
            "read_tokens",
            "write_tokens",
            "read_preferences",
            "write_preferences",
        ],
        settings_key="api_frontend_user_key",
    ),
    "api_chat_user_key": APIKeyConfig(
        client="chat",
        service="user-management-access",
        permissions=[
            "read_users",
            "read_preferences",
        ],
        settings_key="api_chat_user_key",
    ),
    "api_office_user_key": APIKeyConfig(
        client="office",
        service="user-management-access",
        permissions=[
            "read_users",
            "read_tokens",
            "write_tokens",
        ],
        settings_key="api_office_user_key",
    ),
    "api_meetings_user_key": APIKeyConfig(
        client="meetings",
        service="user-management-access",
        permissions=[
            "read_users",
            "read_preferences",
        ],
        settings_key="api_meetings_user_key",
    ),
}

# Service-level permissions fallback (optional, for legacy support)
SERVICE_PERMISSIONS = {
    "user-management-access": [
        "read_users",
        "write_users",
        "read_tokens",
        "write_tokens",
        "read_preferences",
        "write_preferences",
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


# For compatibility with old tests and code
def get_client_permissions(client_name: str) -> list[str]:
    return shared_get_client_permissions(
        client_name,
        {
            "frontend": [
                "read_users",
                "write_users",
                "read_tokens",
                "write_tokens",
                "read_preferences",
                "write_preferences",
            ],
            "chat": [
                "read_users",
                "read_preferences",
            ],
            "office": [
                "read_users",
                "read_tokens",
                "write_tokens",
            ],
            "meetings": [
                "read_users",
                "read_preferences",
            ],
        },
    )


def client_has_permission(client_name: str, required_permission: str) -> bool:
    return shared_client_has_permission(
        client_name,
        required_permission,
        {
            "frontend": [
                "read_users",
                "write_users",
                "read_tokens",
                "write_tokens",
                "read_preferences",
                "write_preferences",
            ],
            "chat": [
                "read_users",
                "read_preferences",
            ],
            "office": [
                "read_users",
                "read_tokens",
                "write_tokens",
            ],
            "meetings": [
                "read_users",
                "read_preferences",
            ],
        },
    )
