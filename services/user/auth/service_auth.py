"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.

**Terminology Clarification:**
- api_key_name: The identifier/name for an API key (e.g., "api-frontend-user-key")
- api_key_value: The actual secret value stored in environment variables (e.g., "test-FRONTEND-123...")
- service_name: The service identifier (e.g., "user-management-access")
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable

from fastapi import Request

from services.common.http_errors import AuthError, ServiceError
from services.common.logging_config import get_logger
from services.user.settings import get_settings
from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
    get_client_from_api_key,
    get_permissions_from_api_key,
    has_permission,
    validate_service_permissions,
    make_verify_service_authentication,
    make_service_permission_required,
)

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
}

# Client-level permissions
CLIENT_PERMISSIONS = {
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
verify_service_authentication = make_verify_service_authentication(API_KEY_CONFIGS, get_settings)

def service_permission_required(required_permissions: List[str]) -> Callable[[Request], Any]:
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )

# Backward compatibility functions for existing imports
def get_current_service(request: Request) -> Optional[str]:
    """Get the current service name from request state."""
    return getattr(request.state, "service_name", None)

def get_service_auth() -> Any:
    """Get service auth instance for backward compatibility."""
    class ServiceAuth:
        def verify_api_key_value(self, api_key: str) -> Optional[str]:
            api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
            return verify_api_key(api_key, api_key_mapping)
        
        def is_valid_client(self, client_name: str) -> bool:
            api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
            # Check if any API key config has this client name
            return any(config.client == client_name for config in api_key_mapping.values())
    
    return ServiceAuth()

def require_service_auth(allowed_clients: Optional[List[str]] = None) -> Callable[[Request], Any]:
    """Create a service auth dependency with optional client restrictions."""
    async def dependency(request: Request) -> str:
        service_name = await verify_service_authentication(request)
        if allowed_clients:
            client_name = getattr(request.state, "client_name", None)
            if client_name not in allowed_clients:
                raise AuthError(message=f"Client {client_name} not allowed", status_code=403)
        return service_name
    return dependency

def get_client_permissions(client_name: str) -> List[str]:
    """Get permissions for a client name."""
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    # Find any API key config with this client name and return its permissions
    for config in api_key_mapping.values():
        if config.client == client_name:
            return config.permissions
    return []

def client_has_permission(client_name: str, required_permission: str) -> bool:
    """Check if a client has a specific permission."""
    permissions = get_client_permissions(client_name)
    return required_permission in permissions
