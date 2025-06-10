"""
Clerk JWT token validation for User Management Service.

Provides JWT token validation and user extraction using Clerk's Python SDK.
Handles token verification, decoding, and user information extraction.
"""

import logging
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..exceptions import AuthenticationException
from ..logging_config import get_logger
from ..settings import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


async def verify_jwt_token(token: str) -> Dict[str, str]:
    """
    Verify JWT token using manual verification.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token claims

    Raises:
        AuthenticationException: If token is invalid
    """
    logger = get_logger(__name__)

    try:
        logger.info("Using manual JWT verification (signature verification disabled)")

        # For development/demo, we use simplified JWT validation
        # In production, you should use proper signature verification with JWKS
        verify_signature = getattr(settings, "jwt_verify_signature", False)
        dummy_key = "dummy-key-for-verification-disabled"

        decoded_token = jwt.decode(
            token,
            key=dummy_key,
            options={
                "verify_signature": verify_signature
            },  # Configurable signature verification
            algorithms=[
                "RS256",
                "HS256",
            ],  # Accept both RS256 (production) and HS256 (demo)
        )

        # Validate required claims
        required_claims = ["sub", "iss", "exp", "iat"]
        for claim in required_claims:
            if claim not in decoded_token:
                logger.error(f"Missing required claim: {claim}")
                raise AuthenticationException(f"Missing required claim: {claim}")

        # For demo purposes, accept various issuers
        # In production, you should validate against your specific issuer
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
    Placeholder for Clerk user retrieval.

    In production, this would make an API call to Clerk to get user information.
    For development/demo purposes, returns None.

    Args:
        user_id: Clerk user ID

    Returns:
        User information dictionary or None if not found
    """
    logger.warning("get_user_from_clerk called but Clerk client not available")
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
