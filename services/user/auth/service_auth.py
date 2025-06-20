"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.

**Terminology Clarification:**
- api_key_name: The identifier/name for an API key (e.g., "api-frontend-user-key")
- api_key_value: The actual secret value stored in environment variables (e.g., "test-FRONTEND-123...")
- service_name: The service identifier (e.g., "user-management-access")
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from services.user.exceptions import (
    AuthenticationException,
    AuthorizationException,
)
from services.user.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class APIKeyConfig:
    """Configuration for an API key."""

    client: str
    service: str
    permissions: List[str]


# API Key Name to Service/Client mapping with permissions
# NOTE: These are KEY NAMES, not the actual secret values!
# The actual values come from environment variables.
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    # Frontend (Next.js API) keys - full permissions for user-facing operations
    "api-frontend-office-key": APIKeyConfig(
        client="frontend",
        service="office-service-access",
        permissions=[
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
        ],
    ),
    "api-frontend-user-key": APIKeyConfig(
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
    ),
    "api-frontend-chat-key": APIKeyConfig(
        client="frontend",
        service="chat-service-access",
        permissions=["read_chats", "write_chats", "read_threads", "write_threads"],
    ),
    # Service-to-service keys - limited permissions
    "api-chat-user-key": APIKeyConfig(
        client="chat-service",
        service="user-management-access",
        permissions=["read_users", "read_preferences"],  # Read-only for user context
    ),
    "api-chat-office-key": APIKeyConfig(
        client="chat-service",
        service="office-service-access",
        permissions=[
            "read_emails",
            "read_calendar",
            "read_files",
        ],  # No write permissions
    ),
    "api-office-user-key": APIKeyConfig(
        client="office-service",
        service="user-management-access",
        permissions=[
            "read_users",
            "read_tokens",
            "write_tokens",
        ],  # Can manage tokens
    ),
}


class ServiceAPIKeyAuth:
    """
    Service API key authentication handler.

    This class manages authentication for this specific service by:
    1. Reading actual API key values from environment variables
    2. Mapping them to service names for authorization
    """

    def __init__(self):
        # Map actual API key values to service names
        self.api_key_value_to_service: Dict[str, str] = {}

        # Only register API keys that belong to this service (user-management)
        if get_settings().api_frontend_user_key:
            self.api_key_value_to_service[get_settings().api_frontend_user_key] = (
                "user-management-access"
            )

        if get_settings().api_office_user_key:
            self.api_key_value_to_service[get_settings().api_office_user_key] = (
                "office-service-access"
            )

        logger.info(
            f"ServiceAPIKeyAuth initialized with {len(self.api_key_value_to_service)} API keys"
        )

    def verify_api_key_value(self, api_key_value: str) -> Optional[str]:
        """
        Verify an API key value and return the associated service name.

        Args:
            api_key_value: The actual API key secret value from the request

        Returns:
            Service name if the API key value is valid, None otherwise
        """
        return self.api_key_value_to_service.get(api_key_value)

    def is_valid_service(self, service_name: str) -> bool:
        """
        Check if service name is valid and authorized for this service.

        Args:
            service_name: Name of the service

        Returns:
            True if service is authorized
        """
        authorized_services = [
            "user-management-access",
            "office-service-access",
        ]
        return service_name in authorized_services


# Global service auth instance
_service_auth: ServiceAPIKeyAuth | None = None


def get_service_auth() -> ServiceAPIKeyAuth:
    """Get the global service auth instance, creating it if necessary."""
    global _service_auth
    if _service_auth is None:
        _service_auth = ServiceAPIKeyAuth()
    return _service_auth


async def get_api_key_value_from_request(request: Request) -> Optional[str]:
    """
    Extract API key value from request headers.

    Supports multiple header formats:
    - Authorization: Bearer <api_key_value>
    - X-API-Key: <api_key_value>
    - X-Service-Key: <api_key_value>

    Args:
        request: FastAPI request object

    Returns:
        API key value if found, None otherwise
    """
    # Try X-API-Key header (preferred)
    api_key_value = request.headers.get("X-API-Key")
    if api_key_value:
        return api_key_value

    # Try Authorization header
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]  # Remove "Bearer " prefix

    # Try X-Service-Key header (legacy)
    service_key = request.headers.get("X-Service-Key")
    if service_key:
        return service_key

    return None


async def verify_service_authentication(request: Request) -> str:
    """
    Verify service authentication via API key value.

    Args:
        request: FastAPI request object

    Returns:
        Service name if authentication succeeds

    Raises:
        HTTPException: If authentication fails
    """
    api_key_value = await get_api_key_value_from_request(request)

    if not api_key_value:
        logger.warning("Missing API key in request headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    service_name = get_service_auth().verify_api_key_value(api_key_value)

    if not service_name:
        logger.warning(f"Invalid API key value: {api_key_value[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store API key and service info in request state for permission checking
    request.state.api_key_value = api_key_value
    request.state.service_name = service_name
    # Map service names to client names
    service_to_client = {
        "user-management-access": "frontend",
        "office-service-access": "office",
    }
    request.state.client_name = service_to_client.get(
        service_name, get_client_from_api_key_name_lookup(api_key_value)
    )

    logger.info(
        f"Service authenticated: {service_name} (client: {request.state.client_name})"
    )
    return service_name


async def get_current_service(request: Request) -> str:
    """
    FastAPI dependency to get current authenticated service.

    Args:
        request: FastAPI request object

    Returns:
        Service name

    Raises:
        HTTPException: If service authentication fails
    """
    try:
        service_name = await verify_service_authentication(request)
        return service_name

    except AuthenticationException as e:
        logger.warning(f"Service authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "ServiceAuthenticationError", "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    except AuthorizationException as e:
        logger.warning(f"Service authorization failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ServiceAuthorizationError", "message": e.message},
        )

    except Exception as e:
        logger.error(f"Unexpected service authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ServiceAuthenticationError",
                "message": "Authentication failed",
            },
        )


def require_service_auth(allowed_services: list = None):
    """
    Decorator factory for service authentication with specific service restrictions.

    Args:
        allowed_services: List of allowed service names (optional)

    Returns:
        FastAPI dependency function
    """

    async def service_dependency(request: Request) -> str:
        service_name = await get_current_service(request)

        if allowed_services and service_name not in allowed_services:
            logger.warning(
                f"Service {service_name} not in allowed list: {allowed_services}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ServiceAuthorizationError",
                    "message": f"Service {service_name} not authorized for this endpoint",
                },
            )

        return service_name

    return service_dependency


# Legacy functions for backwards compatibility with global API_KEY_CONFIGS
# These work with API key names, not values


def verify_api_key_name(api_key_name: str) -> Optional[str]:
    """
    Verify an API key name and return the service name it's authorized for.

    NOTE: This function works with key NAMES, not actual secret values!

    Args:
        api_key_name: The API key name/identifier (e.g., "api-frontend-user-key")

    Returns:
        Service name if valid, None if invalid
    """
    if not api_key_name:
        return None

    key_config = API_KEY_CONFIGS.get(api_key_name)
    if not key_config:
        return None

    return key_config.service


def get_client_from_api_key_name(api_key_name: str) -> Optional[str]:
    """Get the client name from an API key name."""
    key_config = API_KEY_CONFIGS.get(api_key_name)
    return key_config.client if key_config else None


def get_permissions_from_api_key_name(api_key_name: str) -> List[str]:
    """Get the permissions for an API key name."""
    key_config = API_KEY_CONFIGS.get(api_key_name)
    return key_config.permissions if key_config else []


def get_client_from_api_key_name_lookup(api_key_value: str) -> Optional[str]:
    """
    Attempt to find client name by looking up API key value in configurations.
    This is a fallback for cases where we can't determine the client otherwise.
    """
    # For now, return None since we can't reverse-lookup from value to name
    # without storing additional mapping
    return None


def has_permission_by_key_name(api_key_name: str, required_permission: str) -> bool:
    """Check if an API key name has a specific permission."""
    permissions = get_permissions_from_api_key_name(api_key_name)
    return required_permission in permissions


async def validate_service_permissions(
    service_name: str,
    required_permissions: Optional[List[str]] = None,
    api_key_value: Optional[str] = None,
) -> bool:
    """
    Validate that a service has the required permissions.

    Args:
        service_name: The authenticated service name
        required_permissions: List of required permissions
        api_key_value: The API key value used (for granular permission checking)

    Returns:
        True if service has all required permissions, False otherwise
    """
    if not required_permissions:
        return True

    # For now, use service-level permissions since we don't have
    # a reverse mapping from api_key_value to api_key_name
    service_permissions = {
        "user-management-access": [
            "read_users",
            "write_users",
            "read_tokens",
            "write_tokens",
            "read_preferences",
            "write_preferences",
        ],
        "office-service-access": [
            "read_users",
            "read_tokens",
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
        ],
        "chat-service-access": [
            "read_users",
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
        ],
        "api-gateway-access": ["read_users"],
    }

    allowed_permissions = service_permissions.get(service_name, [])
    return all(perm in allowed_permissions for perm in required_permissions)


class ServiceAuthRequired:
    """
    Dependency class for service authentication with permission validation.
    """

    def __init__(self, permissions: list = None, allowed_services: list = None):
        self.permissions = permissions or []
        self.allowed_services = allowed_services

    async def __call__(self, request: Request) -> str:
        service_name = await get_current_service(request)

        # Check service restrictions
        if self.allowed_services and service_name not in self.allowed_services:
            logger.warning(
                f"Service {service_name} not in allowed list: {self.allowed_services}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ServiceAuthorizationError",
                    "message": f"Service {service_name} not authorized for this endpoint",
                },
            )

        # Check permissions
        if self.permissions:
            api_key_value = getattr(request.state, "api_key_value", None)
            has_permissions = await validate_service_permissions(
                service_name, self.permissions, api_key_value
            )
            if not has_permissions:
                logger.warning(
                    f"Service {service_name} missing required permissions: {self.permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "ServiceAuthorizationError",
                        "message": f"Service {service_name} lacks required permissions",
                    },
                )

        return service_name


class ServicePermissionRequired:
    """
    Dependency class that requires specific permissions for service access.

    This ensures that the authenticated service has the necessary permissions
    to perform the requested operation.
    """

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    async def __call__(self, request: Request) -> str:
        # First ensure service is authenticated
        service_name = await get_current_service(request)

        # Then check permissions
        api_key_value = getattr(request.state, "api_key_value", None)
        has_permissions = await validate_service_permissions(
            service_name, self.required_permissions, api_key_value
        )

        if not has_permissions:
            logger.warning(
                f"Service {service_name} missing required permissions: {self.required_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ServiceAuthorizationError",
                    "message": f"Service {service_name} lacks required permissions: {', '.join(self.required_permissions)}",
                },
            )

        return service_name
