"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from ..exceptions import AuthenticationException, AuthorizationException
from ..settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class APIKeyConfig:
    """Configuration for an API key."""

    client: str
    service: str
    permissions: List[str]


# API Key to Service/Client mapping with permissions
API_KEYS: Dict[str, APIKeyConfig] = {
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
    """Service API key authentication handler."""

    def __init__(self):
        self.valid_api_keys = {}
        # Only accept this service's own API key for access
        if settings.api_key_user_management:
            self.valid_api_keys[settings.api_key_user_management] = (
                "user-management-access"
            )

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """
        Verify service API key and return service name.

        Args:
            api_key: The API key to verify

        Returns:
            Service name if valid, None otherwise
        """
        return self.valid_api_keys.get(api_key)

    def is_valid_service(self, service_name: str) -> bool:
        """
        Check if service name is valid and authorized.

        Args:
            service_name: Name of the service

        Returns:
            True if service is authorized
        """
        authorized_services = [
            "user-management-access",
        ]
        return service_name in authorized_services


# Global service auth instance
service_auth = ServiceAPIKeyAuth()


async def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    Extract API key from request headers.

    Supports multiple header formats:
    - Authorization: Bearer <api_key>
    - X-API-Key: <api_key>
    - X-Service-Key: <api_key>

    Args:
        request: FastAPI request object

    Returns:
        API key if found, None otherwise
    """
    # Try X-API-Key header (preferred)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

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
    Verify service authentication via API key.

    Args:
        request: FastAPI request object

    Returns:
        Service name if authentication succeeds

    Raises:
        HTTPException: If authentication fails
    """
    api_key = await get_api_key_from_request(request)

    if not api_key:
        logger.warning("Missing API key in request headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    service_name = verify_api_key(api_key)

    if not service_name:
        logger.warning(f"Invalid API key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store API key and client info in request state for permission checking
    request.state.api_key = api_key
    request.state.service_name = service_name
    request.state.client_name = get_client_from_api_key(api_key)

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


def verify_api_key(api_key: str) -> Optional[str]:
    """
    Verify an API key and return the service name it's authorized for.

    Args:
        api_key: The API key to verify

    Returns:
        Service name if valid, None if invalid
    """
    if not api_key:
        return None

    key_config = API_KEYS.get(api_key)
    if not key_config:
        return None

    return key_config.service


def get_client_from_api_key(api_key: str) -> Optional[str]:
    """Get the client name from an API key."""
    key_config = API_KEYS.get(api_key)
    return key_config.client if key_config else None


def get_permissions_from_api_key(api_key: str) -> List[str]:
    """Get the permissions for an API key."""
    key_config = API_KEYS.get(api_key)
    return key_config.permissions if key_config else []


def has_permission(api_key: str, required_permission: str) -> bool:
    """Check if an API key has a specific permission."""
    permissions = get_permissions_from_api_key(api_key)
    return required_permission in permissions


async def validate_service_permissions(
    service_name: str,
    required_permissions: Optional[List[str]] = None,
    api_key: Optional[str] = None,
) -> bool:
    """
    Validate that a service has the required permissions.

    Args:
        service_name: The authenticated service name
        required_permissions: List of required permissions
        api_key: The API key used (for granular permission checking)

    Returns:
        True if service has all required permissions, False otherwise
    """
    if not required_permissions:
        return True

    # If we have the API key, use granular permission checking
    if api_key:
        key_permissions = get_permissions_from_api_key(api_key)
        return all(perm in key_permissions for perm in required_permissions)

    # Fallback to service-level permissions
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

        # Check allowed services
        if self.allowed_services and service_name not in self.allowed_services:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ServiceAuthorizationError",
                    "message": f"Service {service_name} not authorized",
                },
            )

        # Check permissions
        if not await validate_service_permissions(service_name, self.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ServicePermissionError",
                    "message": f"Service {service_name} lacks required permissions",
                },
            )

        return service_name


class ServicePermissionRequired:
    """
    Dependency to check if the authenticated service has specific permissions.

    Usage:
        @app.get("/emails", dependencies=[Depends(ServicePermissionRequired(["send_emails"]))])
        async def send_email():
            # This endpoint requires send_emails permission
            pass
    """

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    async def __call__(self, request: Request) -> str:
        # First ensure service is authenticated
        service_name = await verify_service_authentication(request)

        # Check if the API key has the required permissions
        api_key = getattr(request.state, "api_key", None)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key not found in request state",
            )

        # Validate permissions
        if not await validate_service_permissions(
            service_name, self.required_permissions, api_key
        ):
            client_name = getattr(request.state, "client_name", "unknown")
            logger.warning(
                f"Permission denied: {client_name} lacks permissions {self.required_permissions}",
                extra={
                    "service": service_name,
                    "client": client_name,
                    "required_permissions": self.required_permissions,
                    "api_key_prefix": api_key[:8] if api_key else None,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {self.required_permissions}",
            )

        return service_name
