"""
Authentication module for Chat Service.

Provides API key based authentication for incoming requests from the frontend.
"""

import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from services.chat.settings import get_settings

logger = logging.getLogger(__name__)


class ChatServiceAuth:
    """
    Chat service API key authentication handler.

    Manages authentication for incoming requests to the chat service.
    """

    def __init__(self):
        # Map actual API key values directly to client service names
        self.api_key_value_to_client: Dict[str, str] = {}

        # Register API keys that can access this chat service
        if get_settings().api_frontend_chat_key:
            self.api_key_value_to_client[get_settings().api_frontend_chat_key] = (
                "frontend"
            )

        logger.info(
            f"ChatServiceAuth initialized with {len(self.api_key_value_to_client)} API keys"
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
        authorized_clients = ["frontend"]
        return client_name in authorized_clients


# Global service auth instance
_chat_auth: ChatServiceAuth | None = None


def get_chat_auth() -> ChatServiceAuth:
    """Get the global chat auth instance, creating it if necessary."""
    global _chat_auth
    if _chat_auth is None:
        _chat_auth = ChatServiceAuth()
    return _chat_auth


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


async def verify_chat_authentication(request: Request) -> str:
    """
    Verify chat service authentication via API key value.

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    client_name = get_chat_auth().verify_api_key_value(api_key_value)

    if not client_name:
        logger.warning(f"Invalid API key value: {api_key_value[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store API key and client info in request state
    request.state.api_key_value = api_key_value
    request.state.client_name = client_name

    logger.info(f"Chat service authenticated: {client_name}")
    return client_name


def require_chat_auth(allowed_clients: List[str] = None):
    """
    Decorator factory for chat authentication with specific client restrictions.

    Args:
        allowed_clients: List of allowed client names (e.g., ["frontend"])

    Returns:
        FastAPI dependency function
    """

    async def chat_dependency(request: Request) -> str:
        client_name = await verify_chat_authentication(request)

        if allowed_clients and client_name not in allowed_clients:
            logger.warning(
                f"Client {client_name} not in allowed list: {allowed_clients}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ChatAuthorizationError",
                    "message": f"Client {client_name} not authorized for this endpoint",
                },
            )

        return client_name

    return chat_dependency


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
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
            "read_feedback",
            "write_feedback",
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