"""
Shared API key authentication and authorization helpers for Briefly services.

Each service should define its own API_KEY_CONFIGS and get_settings function, and pass them to these helpers.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request

from services.common.http_errors import AuthError, ServiceError
from services.common.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class APIKeyConfig:
    client: str
    service: str
    permissions: List[str]
    settings_key: str  # The key name in settings to look up the actual API key value


def build_api_key_mapping(
    api_key_configs: Dict[str, APIKeyConfig], get_settings: Callable[[], Any]
) -> Dict[str, APIKeyConfig]:
    """
    Build a mapping from actual API key values to their configurations.
    """
    settings = get_settings()
    api_key_mapping = {}
    for _config_name, config in api_key_configs.items():
        actual_key_value = getattr(settings, config.settings_key, None)
        if actual_key_value:
            api_key_mapping[actual_key_value] = config
        else:
            logger.warning(f"API key not found in settings: {config.settings_key}")
    return api_key_mapping


def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    Extract API key from request headers (supports X-API-Key, Authorization: Bearer, X-Service-Key).
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    service_key = request.headers.get("X-Service-Key")
    if service_key:
        return service_key
    return None


def verify_api_key(
    api_key: str, api_key_mapping: Dict[str, APIKeyConfig]
) -> Optional[str]:
    """
    Verify an API key and return the service name it's authorized for.
    """
    if not api_key:
        return None
    key_config = api_key_mapping.get(api_key)
    if not key_config:
        return None
    return key_config.service


def get_client_from_api_key(
    api_key: str, api_key_mapping: Dict[str, APIKeyConfig]
) -> Optional[str]:
    key_config = api_key_mapping.get(api_key)
    return key_config.client if key_config else None


def get_permissions_from_api_key(
    api_key: str, api_key_mapping: Dict[str, APIKeyConfig]
) -> List[str]:
    key_config = api_key_mapping.get(api_key)
    return key_config.permissions if key_config else []


def has_permission(
    api_key: str, required_permission: str, api_key_mapping: Dict[str, APIKeyConfig]
) -> bool:
    permissions = get_permissions_from_api_key(api_key, api_key_mapping)
    return required_permission in permissions


def get_client_permissions(
    client_name: str, client_permissions: Dict[str, List[str]]
) -> List[str]:
    return client_permissions.get(client_name, [])


def client_has_permission(
    client_name: str, required_permission: str, client_permissions: Dict[str, List[str]]
) -> bool:
    permissions = get_client_permissions(client_name, client_permissions)
    return required_permission in permissions


def get_service_permissions(
    service_name: str, service_permissions: Dict[str, List[str]]
) -> List[str]:
    return service_permissions.get(service_name, [])


def validate_service_permissions(
    service_name: str,
    required_permissions: Optional[List[str]],
    api_key: Optional[str],
    api_key_mapping: Dict[str, APIKeyConfig],
    service_permissions: Optional[Dict[str, List[str]]] = None,
) -> bool:
    """
    Validate that a service has the required permissions.
    """
    if not required_permissions:
        return True
    if api_key:
        key_permissions = get_permissions_from_api_key(api_key, api_key_mapping)
        return all(perm in key_permissions for perm in required_permissions)
    if service_permissions:
        allowed_permissions = service_permissions.get(service_name, [])
        return all(perm in allowed_permissions for perm in required_permissions)
    return False


# FastAPI dependencies (parameterized)
def make_verify_service_authentication(
    api_key_configs: Dict[str, APIKeyConfig], get_settings: Callable[[], Any]
) -> Callable[[Request], str]:
    def verify_service_authentication(request: Request) -> str:
        """Synchronously verify the API key from the request and return the service name."""
        api_key = get_api_key_from_request(request)
        api_key_mapping = build_api_key_mapping(api_key_configs, get_settings)
        if not api_key:
            logger.warning("Missing API key in request headers")
            raise AuthError(message="API key required", status_code=401)
        service_name = verify_api_key(api_key, api_key_mapping)
        if not service_name:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            raise AuthError(message="Invalid API key", status_code=403)
        request.state.api_key = api_key
        request.state.service_name = service_name
        request.state.client_name = get_client_from_api_key(api_key, api_key_mapping)
        logger.info(
            f"Service authenticated: {service_name} (client: {request.state.client_name})"
        )
        return service_name

    return verify_service_authentication


def make_service_permission_required(
    required_permissions: List[str],
    api_key_configs: Dict[str, APIKeyConfig],
    get_settings: Callable[[], Any],
    service_permissions: Optional[Dict[str, List[str]]] = None,
) -> Callable[[Request], Any]:
    async def dependency(request: Request) -> str:
        verify_service_authentication = make_verify_service_authentication(
            api_key_configs, get_settings
        )
        service_name = verify_service_authentication(request)
        api_key_mapping = build_api_key_mapping(api_key_configs, get_settings)
        api_key = getattr(request.state, "api_key", None)
        if not api_key:
            raise ServiceError(
                message="API key not found in request state", status_code=500
            )
        if not validate_service_permissions(
            service_name,
            required_permissions,
            api_key,
            api_key_mapping,
            service_permissions,
        ):
            client_name = getattr(request.state, "client_name", "unknown")
            logger.warning(
                f"Permission denied: {client_name} lacks permissions {required_permissions}",
                extra={
                    "service": service_name,
                    "client": client_name,
                    "required_permissions": required_permissions,
                    "api_key_prefix": api_key[:8] if api_key else None,
                },
            )
            raise AuthError(
                message=f"Insufficient permissions. Required: {required_permissions}",
                status_code=403,
            )
        return service_name

    return dependency
