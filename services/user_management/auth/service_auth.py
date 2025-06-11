"""
Service-to-service API key authentication for User Management Service.

Provides API key based authentication for internal service communication.
Validates service API keys and manages service-level access control.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException, Request, status

from services.common.auth import (
    get_api_key_from_request,
    get_client_from_api_key,
    validate_service_permissions,
    verify_api_key,
)

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
        # Use the shared validation logic from common.auth
        from services.common.auth import (
            ServicePermissionRequired as CommonServicePermissionRequired,
        )

        # Delegate to the common implementation (which handles authentication and validation)
        common_validator = CommonServicePermissionRequired(self.required_permissions)
        return await common_validator(request)
