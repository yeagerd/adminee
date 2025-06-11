"""
Shared API key authentication and authorization for all services.

Provides APIKeyConfig dataclass and common authentication utilities that can be
used across all services for consistent service-to-service authentication.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class APIKeyConfig:
    """Configuration for an API key."""

    client: str
    service: str
    permissions: List[str]


# Centralized API Key to Service/Client mapping with permissions
# This serves as the authoritative source for all service API key configurations
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
    # Service-to-service keys - limited permissions with principle of least privilege
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
    # Legacy dev keys (for backward compatibility during transition)
    "dev-service-key": APIKeyConfig(
        client="legacy",
        service="user-management-access",
        permissions=["read_users", "write_users", "read_tokens", "write_tokens"],
    ),
    "dev-office-key": APIKeyConfig(
        client="legacy",
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
}


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

    # Fallback to service-level permissions (expanded to include all services)
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
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
        ],
        "chat-service-access": [
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
        ],
    }

    allowed_permissions = service_permissions.get(service_name, [])
    return all(perm in allowed_permissions for perm in required_permissions)


class ServicePermissionRequired:
    """
    Dependency to check if the authenticated service has specific permissions.

    Usage:
        @app.post("/emails/send", dependencies=[Depends(ServicePermissionRequired(["send_emails"]))])
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


async def optional_service_auth(request: Request) -> Optional[str]:
    """
    Optional service authentication that doesn't raise errors.

    This can be used for endpoints that support both service-to-service
    and direct user access.

    Args:
        request: FastAPI request object

    Returns:
        Service name if authenticated, None otherwise
    """
    try:
        return await verify_service_authentication(request)
    except HTTPException:
        return None
