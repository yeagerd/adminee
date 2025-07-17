"""
Authentication utilities for the Office Service.

Provides authentication and authorization functionality for both
service-to-service communication and user requests through the gateway.
"""

import time
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.http_errors import AuthError, ServiceError, ValidationError
from services.common.logging_config import get_logger
from services.office.core.settings import get_settings

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


def verify_api_key(api_key: str) -> Optional[str]:
    """
    Verify API key and return service name.

    Args:
        api_key: API key to verify

    Returns:
        Service name if valid, None otherwise
    """
    settings = get_settings()
    
    # Check against known API keys
    if api_key == settings.api_frontend_office_key:
        return "frontend"
    elif api_key == settings.api_chat_office_key:
        return "chat"
    elif api_key == settings.api_user_office_key:
        return "user"
    
    return None


def get_client_from_api_key(api_key: str) -> str:
    """
    Get client name from API key.

    Args:
        api_key: API key

    Returns:
        Client name
    """
    service_name = verify_api_key(api_key)
    if service_name:
        return service_name
    return "unknown"


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
        raise AuthError(message="API key required", status_code=401)

    service_name = verify_api_key(api_key)

    if not service_name:
        logger.warning(f"Invalid API key: {api_key[:8]}...")
        raise AuthError(message="Invalid API key", status_code=401)

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
    FastAPI dependency to get current authenticated client service.

    Args:
        request: FastAPI request object

    Returns:
        Client service name (e.g., "frontend", "chat", "user")

    Raises:
        HTTPException: If service authentication fails
    """
    try:
        service_name = await verify_service_authentication(request)
        return service_name

    except AuthError as e:
        logger.warning(f"Service authentication failed: {e.message}")
        raise e

    except ServiceError as e:
        logger.warning(f"Service authorization failed: {e.message}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected service authentication error: {e}")
        raise ServiceError(message="Authentication failed")


async def get_current_user_from_gateway_headers(request: Request) -> Optional[str]:
    """
    Extract user ID from gateway headers (X-User-Id).

    This function handles authentication when the request comes through the gateway,
    which forwards user identity via custom headers instead of JWT tokens.

    Args:
        request: FastAPI request object

    Returns:
        User ID from gateway headers or None if not present
    """
    # Check for gateway headers
    user_id = request.headers.get("X-User-Id")
    if user_id:
        logger.debug(
            "User authenticated via gateway headers", extra={"user_id": user_id}
        )
        return user_id

    return None


async def get_current_user_flexible(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Flexible authentication that supports both gateway headers and JWT tokens.

    This function first checks for gateway headers (X-User-Id), and if not present,
    falls back to JWT token validation. This allows the service to work both
    directly (with JWT tokens) and through the gateway (with custom headers).

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token credentials (optional)

    Returns:
        User ID from either gateway headers or JWT token

    Raises:
        HTTPException: If authentication fails
    """
    # First try gateway headers
    user_id = await get_current_user_from_gateway_headers(request)
    if user_id:
        return user_id

    # Fall back to JWT token if no gateway headers
    if not credentials:
        logger.warning("No authentication credentials provided")
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # For now, we'll use a simple JWT validation
        # In a full implementation, you'd want to verify the JWT signature
        import jwt
        from services.office.core.settings import get_settings
        
        settings = get_settings()
        token_claims = jwt.decode(
            credentials.credentials, 
            settings.nextauth_secret, 
            algorithms=["HS256"]
        )
        
        user_id = token_claims.get("sub")
        if not user_id:
            raise AuthError(message="Invalid token: missing subject")
            
        logger.debug(
            "User authenticated via JWT token", extra={"user_id": user_id}
        )
        return user_id
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unexpected JWT authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    FastAPI dependency to extract and validate current user ID.

    This function supports both gateway headers and JWT tokens for authentication.
    It first checks for gateway headers (X-User-Id), and if not present,
    falls back to JWT token validation.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token credentials (optional)

    Returns:
        User ID extracted from either gateway headers or JWT token

    Raises:
        HTTPException: If authentication fails
    """
    return await get_current_user_flexible(request, credentials)


def require_office_auth(allowed_clients: Optional[list] = None):
    """
    Factory function to create authentication dependency for office service endpoints.

    Args:
        allowed_clients: List of allowed client service names (e.g., ["frontend", "chat"])

    Returns:
        FastAPI dependency function
    """
    async def require_auth(request: Request) -> str:
        """
        Require service authentication for office service endpoints.

        Args:
            request: FastAPI request object

        Returns:
            Client service name if authentication succeeds

        Raises:
            HTTPException: If authentication fails or client not allowed
        """
        try:
            client_name = await get_current_service(request)

            # Check if client is allowed
            if allowed_clients and client_name not in allowed_clients:
                logger.warning(
                    f"Client {client_name} not allowed for this endpoint. "
                    f"Allowed clients: {allowed_clients}"
                )
                raise AuthError(
                    message=f"Client {client_name} not authorized for this endpoint",
                    status_code=403,
                )

            return client_name

        except AuthError as e:
            logger.warning(f"Office service authentication failed: {e.message}")
            raise HTTPException(status_code=e.status_code, detail=e.message)

        except Exception as e:
            logger.error(f"Unexpected office service authentication error: {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")

    return require_auth
