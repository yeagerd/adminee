"""
API key authentication for Office Service.

Provides service-to-service API key authentication for internal communication.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from .config import settings

logger = logging.getLogger(__name__)


class ServiceAPIKeyAuth:
    """Service API key authentication handler for Office Service."""

    def __init__(self):
        self.valid_api_keys = {}
        # Only accept this service's own API key for access
        if settings.api_key_office:
            self.valid_api_keys[settings.api_key_office] = "office-service-access"

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
            "office-service-access",
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
        HTTPException: If authentication fails
    """
    api_key = await get_api_key_from_request(request)

    if not api_key:
        logger.warning("No API key provided in service request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Service API key required"
        )

    service_name = service_auth.verify_api_key(api_key)

    if not service_name:
        logger.warning(f"Invalid API key provided: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service API key"
        )

    if not service_auth.is_valid_service(service_name):
        logger.warning(f"Unauthorized service: {service_name}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Service not authorized"
        )

    logger.info(f"Service authenticated successfully: {service_name}")
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
