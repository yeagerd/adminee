"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from ..exceptions import AuthenticationException, AuthorizationException
from ..settings import settings

logger = logging.getLogger(__name__)


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
    # Try Authorization header first
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, credentials = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            return credentials

    # Try X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    # Try X-Service-Key header
    service_key = request.headers.get("X-Service-Key")
    if service_key:
        return service_key

    return None


async def verify_service_authentication(request: Request) -> str:
    """
    Verify service authentication and return service name.

    Args:
        request: FastAPI request object

    Returns:
        Service name if authenticated

    Raises:
        AuthenticationException: If authentication fails
    """
    api_key = await get_api_key_from_request(request)

    if not api_key:
        logger.warning("No API key provided in service request")
        raise AuthenticationException("Service API key required")

    service_name = service_auth.verify_api_key(api_key)

    if not service_name:
        logger.warning(f"Invalid API key provided: {api_key[:10]}...")
        raise AuthenticationException("Invalid service API key")

    if not service_auth.is_valid_service(service_name):
        logger.warning(f"Unauthorized service: {service_name}")
        raise AuthorizationException("service_access", "authenticate")

    logger.info(f"Service authenticated successfully: {service_name}")
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


async def validate_service_permissions(
    service_name: str, required_permissions: list = None
) -> bool:
    """
    Validate service permissions for specific operations.

    Args:
        service_name: Name of the service
        required_permissions: List of required permissions

    Returns:
        True if service has required permissions
    """
    if not required_permissions:
        return True

    # Define service permissions
    service_permissions = {
        "user-management-access": [
            "read_users",
            "write_users",
            "read_tokens",
            "write_tokens",
        ],
        "office-service-access": ["read_users", "read_tokens"],
        "chat-service-access": ["read_users"],
        "api-gateway-access": ["read_users"],
    }

    permissions = service_permissions.get(service_name, [])

    # Check if all required permissions are present
    for permission in required_permissions:
        if permission not in permissions:
            logger.warning(
                f"Service {service_name} missing permission: {permission}",
                extra={"service": service_name, "required": required_permissions},
            )
            return False

    return True


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
