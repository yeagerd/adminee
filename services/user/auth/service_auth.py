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
from typing import Dict, List, Optional, Any

from fastapi import Request

from services.common.http_errors import AuthError, ServiceError
from services.common.logging_config import get_logger
from services.user.settings import get_settings

logger = get_logger(__name__)


@dataclass(frozen=True)
class APIKeyConfig:
    """Configuration for an API key."""

    client: str
    service: str
    permissions: List[str]


class ServiceAPIKeyAuth:
    """
    Service API key authentication handler.

    This class manages authentication for this specific service by:
    1. Reading actual API key values from environment variables
    2. Mapping them directly to client service names
    """

    def __init__(self) -> None:
        # Map actual API key values directly to client service names
        self.api_key_value_to_client: Dict[str, str] = {}

        # Register API keys that can access this user service
        frontend_key = get_settings().api_frontend_user_key
        if frontend_key:
            self.api_key_value_to_client[frontend_key] = "frontend"

        chat_key = get_settings().api_chat_user_key
        if chat_key:
            self.api_key_value_to_client[chat_key] = "chat"

        office_key = get_settings().api_office_user_key
        if office_key:
            self.api_key_value_to_client[office_key] = "office"

        logger.info(
            f"ServiceAPIKeyAuth initialized with {len(self.api_key_value_to_client)} API keys"
        )

    def verify_api_key_value(self, api_key_value: str) -> Optional[str]:
        """
        Verify an API key value and return the associated client service name.

        Args:
            api_key_value: The actual API key secret value from the request

        Returns:
            Client service name if the API key value is valid, None otherwise
        """
        return self.api_key_value_to_client.get(api_key_value)

    def is_valid_client(self, client_name: str) -> bool:
        """
        Check if client name is valid and authorized for this service.

        Args:
            client_name: Name of the client service

        Returns:
            True if client is authorized
        """
        authorized_clients = [
            "frontend",
            "chat",
            "office",
        ]
        return client_name in authorized_clients


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
        Client service name if authentication succeeds

    Raises:
        HTTPException: If authentication fails
    """
    api_key_value = await get_api_key_value_from_request(request)

    if not api_key_value:
        logger.warning("Missing API key in request headers")
        raise AuthError(message="API key required")

    client_name = get_service_auth().verify_api_key_value(api_key_value)

    if not client_name:
        logger.warning(f"Invalid API key value: {api_key_value[:8]}...")
        raise AuthError(message="Invalid API key")

    # Store API key and client info in request state
    request.state.api_key_value = api_key_value
    request.state.client_name = client_name

    logger.info(f"Service authenticated: {client_name}")
    return client_name


async def get_current_service(request: Request) -> str:
    """
    FastAPI dependency to get current authenticated client service.

    Args:
        request: FastAPI request object

    Returns:
        Client service name (e.g., "frontend", "chat", "office")

    Raises:
        HTTPException: If service authentication fails
    """
    try:
        client_name = await verify_service_authentication(request)
        return client_name

    except AuthError as e:
        logger.warning(f"Service authentication failed: {e.message}")
        raise e

    except ServiceError as e:
        logger.warning(f"Service authorization failed: {e.message}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected service authentication error: {e}")
        raise ServiceError(message="Authentication failed")


def require_service_auth(allowed_clients: Optional[List[str]] = None) -> Any:
    """
    Decorator factory for service authentication with specific client restrictions.

    Args:
        allowed_clients: List of allowed client names (e.g., ["frontend", "chat"])

    Returns:
        FastAPI dependency function
    """

    async def service_dependency(request: Request) -> str:
        client_name = await get_current_service(request)

        if allowed_clients and client_name not in allowed_clients:
            logger.warning(
                f"Client {client_name} not in allowed list: {allowed_clients}"
            )
            raise AuthError(
                message=f"Client {client_name} not authorized for this endpoint"
            )

        return client_name

    return service_dependency


# Simple permission checking based on client type
def get_client_permissions(client_name: str) -> List[str]:
    """
    Get the permissions for a client.

    Args:
        client_name: Name of the client service

    Returns:
        List of permissions for the client
    """
    client_permissions = {
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

    return client_permissions.get(client_name, [])


def client_has_permission(client_name: str, required_permission: str) -> bool:
    """
    Check if a client has a specific permission.

    Args:
        client_name: Name of the client service
        required_permission: The permission to check for

    Returns:
        True if client has the permission, False otherwise
    """
    permissions = get_client_permissions(client_name)
    return required_permission in permissions
