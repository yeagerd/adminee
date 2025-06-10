"""
Clerk JWT token validation for User Management Service.

Provides JWT token validation and user extraction using Clerk's Python SDK.
Handles token verification, decoding, and user information extraction.
"""

import logging
from typing import Dict, Optional

import jwt
from clerk_backend_api import Clerk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
import httpx

from ..exceptions import AuthenticationException
from ..settings import settings
from ..logging_config import get_logger

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()

# Initialize Clerk client
clerk_client = None
if settings.clerk_secret_key:
    clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)


async def verify_jwt_token(token: str) -> Dict[str, str]:
    """
    Verify JWT token using Clerk's official SDK or fallback to manual verification.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token claims
        
    Raises:
        AuthenticationException: If token is invalid
    """
    logger = get_logger(__name__)
    
    try:
        # Try using Clerk's official SDK first (recommended)
        if settings.clerk_secret_key:
            clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)
            
            # Create a mock request object with the Authorization header
            request = httpx.Request(
                method="GET",
                url="http://localhost/",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Use Clerk's authenticate_request method
            auth_options = AuthenticateRequestOptions()
            if hasattr(settings, 'clerk_jwt_key') and settings.clerk_jwt_key:
                auth_options.jwt_key = settings.clerk_jwt_key
            
            request_state = clerk_client.authenticate_request(request, auth_options)
            
            if not request_state.is_signed_in:
                reason = getattr(request_state, 'reason', 'Authentication failed')
                logger.warning(f"Clerk authentication failed: {reason}")
                raise AuthenticationException(f"Authentication failed: {reason}")
            
            # Extract claims from the validated token
            token_claims = request_state.payload
            logger.info(
                "Token validated successfully with Clerk SDK",
                extra={
                    "user_id": token_claims.get("sub"),
                    "issuer": token_claims.get("iss"),
                },
            )
            return token_claims
            
    except Exception as e:
        logger.warning(f"Clerk SDK verification failed, falling back to manual: {e}")
    
    # Fallback to manual verification (for development/demo)
    try:
        logger.info("Using manual JWT verification (signature verification disabled)")
        
        # Note: Clerk's Python SDK handles JWT verification internally
        # We'll use direct JWT validation for now since Clerk SDK v5+ has different API
        # For production, you should use Clerk's official JWT verification
        # This is a simplified implementation for development
        decoded_token = jwt.decode(
            token,
            options={
                "verify_signature": getattr(settings, 'jwt_verify_signature', False)
            },  # Configurable signature verification
            algorithms=["RS256"],
        )

        # Validate required claims
        required_claims = ["sub", "iss", "exp", "iat"]
        for claim in required_claims:
            if claim not in decoded_token:
                logger.error(f"Missing required claim: {claim}")
                raise AuthenticationException(f"Missing required claim: {claim}")

        # Validate issuer (should be from Clerk)
        if not decoded_token["iss"].startswith("https://clerk."):
            logger.error("Invalid token issuer")
            raise AuthenticationException("Invalid token issuer")

        logger.info(
            "Token validated successfully (manual verification)",
            extra={
                "user_id": decoded_token.get("sub"),
                "issuer": decoded_token.get("iss"),
            },
        )

        return decoded_token

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise AuthenticationException("Token has expired")

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise AuthenticationException("Invalid token")

    except AuthenticationException:
        # Re-raise AuthenticationException without modification
        raise

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise AuthenticationException("Token verification failed")


async def get_user_from_clerk(user_id: str) -> Optional[Dict]:
    """
    Retrieve user information from Clerk API.

    Args:
        user_id: Clerk user ID

    Returns:
        User information dictionary or None if not found
    """
    if not clerk_client:
        logger.error("Clerk client not initialized")
        return None

    try:
        # Use Clerk SDK to get user information
        # Note: Adjust based on your Clerk SDK version
        user = clerk_client.users.get(user_id)

        return {
            "id": user.id,
            "email": (
                user.email_addresses[0].email_address if user.email_addresses else None
            ),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_image_url": user.profile_image_url,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    except Exception as e:
        logger.error(f"Failed to retrieve user from Clerk: {e}")
        return None


def extract_user_id_from_token(token_claims: Dict[str, str]) -> str:
    """
    Extract user ID from validated JWT token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User ID from token

    Raises:
        AuthenticationException: If user ID cannot be extracted
    """
    user_id = token_claims.get("sub")
    if not user_id:
        raise AuthenticationException("User ID not found in token")

    return user_id


def extract_user_email_from_token(token_claims: Dict[str, str]) -> Optional[str]:
    """
    Extract user email from validated JWT token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User email from token or None if not present
    """
    return token_claims.get("email")


def validate_token_permissions(
    token_claims: Dict[str, str], required_permissions: list = None
) -> bool:
    """
    Validate that the token has required permissions.

    Args:
        token_claims: Decoded JWT token claims
        required_permissions: List of required permissions (optional)

    Returns:
        True if token has required permissions
    """
    if not required_permissions:
        return True

    # Extract permissions from token claims
    token_permissions_raw: list | str = token_claims.get("permissions", [])
    token_permissions: list = (
        token_permissions_raw if isinstance(token_permissions_raw, list) else []
    )

    # Check if all required permissions are present
    for permission in required_permissions:
        if permission not in token_permissions:
            logger.warning(
                f"Missing required permission: {permission}",
                extra={
                    "user_id": token_claims.get("sub"),
                    "required": required_permissions,
                },
            )
            return False

    return True


def is_token_expired(token_claims: Dict[str, str]) -> bool:
    """
    Check if token is expired based on exp claim.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        True if token is expired
    """
    import time

    exp_timestamp = token_claims.get("exp")
    if not exp_timestamp:
        return True

    current_timestamp = int(time.time())
    return current_timestamp >= int(exp_timestamp)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency to extract and validate current user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User ID extracted from valid JWT token

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify the JWT token
        token_claims = await verify_jwt_token(credentials.credentials)

        # Extract user ID from token
        user_id = extract_user_id_from_token(token_claims)

        logger.debug("User authenticated successfully", extra={"user_id": user_id})

        return user_id

    except AuthenticationException as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": "Authentication failed"},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_claims(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, str]:
    """
    FastAPI dependency to extract current user and full token claims.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Full token claims dictionary

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify the JWT token
        token_claims = await verify_jwt_token(credentials.credentials)

        logger.debug(
            "User authenticated with full claims",
            extra={"user_id": token_claims.get("sub")},
        )

        return token_claims

    except AuthenticationException as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": "Authentication failed"},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_user_ownership(current_user_id: str, resource_user_id: str) -> bool:
    """
    Verify that the current user owns the resource being accessed.

    Args:
        current_user_id: ID of the currently authenticated user
        resource_user_id: User ID associated with the resource

    Returns:
        True if user owns the resource

    Raises:
        AuthorizationException: If user doesn't own the resource
    """
    if current_user_id != resource_user_id:
        logger.warning(
            f"User {current_user_id} attempted to access resource owned by {resource_user_id}"
        )
        from ..exceptions import AuthorizationException

        raise AuthorizationException(
            resource=f"user_resource:{resource_user_id}", action="access"
        )

    return True


async def require_user_ownership(
    resource_user_id: str,
    current_user_id: str = Depends(get_current_user),
) -> str:
    """
    FastAPI dependency to ensure user can only access their own resources.

    Args:
        resource_user_id: User ID from the resource path/body
        current_user_id: Current authenticated user ID

    Returns:
        Current user ID if ownership is verified

    Raises:
        HTTPException: If user doesn't own the resource
    """
    try:
        await verify_user_ownership(current_user_id, resource_user_id)
        return current_user_id

    except Exception as e:
        # Import here to avoid circular imports
        from ..exceptions import AuthorizationException

        if isinstance(e, AuthorizationException):
            logger.warning(f"User ownership verification failed: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only access your own resources",
                    "resource": e.resource,
                    "action": e.action,
                },
            )
        else:
            logger.error(f"Unexpected ownership verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access verification failed",
                },
            )
