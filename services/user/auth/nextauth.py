"""
NextAuth JWT token validation for User Management Service.

Provides JWT token validation and user extraction.
Handles token verification, decoding, and user information extraction.
"""

import logging
import time # Added for is_token_expired
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Assuming AuthorizationException might be needed by verify_user_ownership
# If it's defined in services.user.exceptions, it should be imported from there.
# For now, I'll keep the local import style as in clerk.py for verify_user_ownership
# but ideally, this should be a top-level import if not causing circular dependencies.
from services.user.exceptions import AuthenticationException #, AuthorizationException
from services.user.logging_config import get_logger
from services.user.settings import get_settings

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
    logger_instance = get_logger(__name__) # Use a local logger instance

    try:
        logger_instance.info("Using manual JWT verification (signature verification potentially disabled based on settings)")

        verify_signature = getattr(get_settings(), "jwt_verify_signature", True) # Default to True for production
        # In a real NextAuth setup, you'd likely use a public key from a JWKS URL
        # For now, this mirrors clerk.py's dev-friendly behavior.
        # Consider making this more robust if NextAuth implies specific signature verification.

        decoded_token = jwt.decode(
            token,
            # key="YOUR_NEXTAUTH_SECRET_OR_PUBLIC_KEY", # This would be needed for proper verification
            options={
                "verify_signature": verify_signature,
                # "require": ["exp", "iat", "sub"], # PyJWT handles this with verify_exp, verify_iat
            },
            algorithms=["RS256", "HS256"], # Specify algorithms used by NextAuth
            # audience="YOUR_AUDIENCE", # If applicable
            # issuer="YOUR_ISSUER" # If applicable
        )

        # PyJWT's decode handles exp, iat by default if verify_exp, verify_iat are true in options.
        # Validate required claims manually if not covered by PyJWT options.
        required_claims = ["sub", "iss"] # exp, iat are usually handled by PyJWT
        for claim in required_claims:
            if claim not in decoded_token:
                logger_instance.error(f"Missing required claim: {claim}")
                raise AuthenticationException(f"Missing required claim: {claim}")

        logger_instance.info(
            "Token validated successfully",
            extra={
                "user_id": decoded_token.get("sub"),
                "issuer": decoded_token.get("iss"),
            },
        )

        return decoded_token

    except jwt.ExpiredSignatureError:
        logger_instance.warning("JWT token has expired")
        raise AuthenticationException("Token has expired")

    except jwt.InvalidAudienceError:
        logger_instance.warning("Invalid JWT audience")
        raise AuthenticationException("Invalid token audience")

    except jwt.InvalidIssuerError:
        logger_instance.warning("Invalid JWT issuer")
        raise AuthenticationException("Invalid token issuer")

    except jwt.InvalidTokenError as e:
        logger_instance.warning(f"Invalid JWT token: {e}")
        raise AuthenticationException(f"Invalid token: {e}")

    except AuthenticationException:
        raise

    except Exception as e:
        logger_instance.error(f"Token verification failed: {e}")
        raise AuthenticationException(f"Token verification failed: {e}")


def extract_user_id_from_token(token_claims: Dict[str, str]) -> str:
    """
    Extract user ID ('sub' claim) from validated JWT token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User ID from token

    Raises:
        AuthenticationException: If user ID (sub claim) cannot be extracted
    """
    user_id = token_claims.get("sub")
    if not user_id:
        # This case should ideally be caught by 'sub' in required_claims in verify_jwt_token
        raise AuthenticationException("User ID (sub claim) not found in token")
    return user_id


def extract_user_email_from_token(token_claims: Dict[str, str]) -> Optional[str]:
    """
    Extract user email from validated JWT token claims.
    NextAuth tokens might store email in 'email' claim.

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
    Permissions might be in a 'scope' or 'permissions' claim.

    Args:
        token_claims: Decoded JWT token claims
        required_permissions: List of required permissions (optional)

    Returns:
        True if token has required permissions
    """
    if not required_permissions:
        return True

    # Standard OAuth scope claim is a space-separated string.
    # Or it could be a list in a 'permissions' claim.
    # Adjust based on how NextAuth is configured to issue tokens.
    token_permissions_str = token_claims.get("scope", "")
    token_permissions_list = token_claims.get("permissions", [])

    if isinstance(token_permissions_str, str):
        token_permissions = set(token_permissions_str.split())
    elif isinstance(token_permissions_list, list):
        token_permissions = set(token_permissions_list)
    else:
        token_permissions = set()

    logger_instance = get_logger(__name__)
    for permission in required_permissions:
        if permission not in token_permissions:
            logger_instance.warning(
                f"Missing required permission: {permission}",
                extra={
                    "user_id": token_claims.get("sub"),
                    "required": required_permissions,
                    "present": list(token_permissions)
                },
            )
            return False
    return True


def is_token_expired(token_claims: Dict[str, str]) -> bool:
    """
    Check if token is expired based on 'exp' claim.
    Note: PyJWT's decode function already verifies 'exp' if options={"verify_exp": True} (default).
    This function can be a redundant check or used if 'exp' needs to be checked manually
    before full decoding, though that's less common.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        True if token is expired
    """
    exp_timestamp = token_claims.get("exp")
    if exp_timestamp is None: # No expiration claim, treat as problematic or expired
        return True
    return time.time() >= int(exp_timestamp)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency to extract and validate current user ID from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User ID extracted from valid JWT token

    Raises:
        HTTPException: If authentication fails
    """
    logger_instance = get_logger(__name__)
    try:
        token_claims = await verify_jwt_token(credentials.credentials)
        user_id = extract_user_id_from_token(token_claims)
        logger_instance.debug("User authenticated successfully", extra={"user_id": user_id})
        return user_id
    except AuthenticationException as e:
        logger_instance.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger_instance.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": "Authentication failed"},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_claims(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, str]:
    """
    FastAPI dependency to extract current user's full token claims.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Full token claims dictionary

    Raises:
        HTTPException: If authentication fails
    """
    logger_instance = get_logger(__name__)
    try:
        token_claims = await verify_jwt_token(credentials.credentials)
        logger_instance.debug(
            "User authenticated with full claims",
            extra={"user_id": token_claims.get("sub")},
        )
        return token_claims
    except AuthenticationException as e:
        logger_instance.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AuthenticationError", "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger_instance.error(f"Unexpected authentication error: {e}")
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
        AuthorizationException: If user doesn't own the resource (imported locally)
    """
    logger_instance = get_logger(__name__)
    if current_user_id != resource_user_id:
        logger_instance.warning(
            f"User {current_user_id} attempted to access resource owned by {resource_user_id}"
        )
        # This import should ideally be at the top-level if it doesn't cause circular dependencies
        from services.user.exceptions import AuthorizationException
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
        current_user_id: Current authenticated user ID from token

    Returns:
        Current user ID if ownership is verified

    Raises:
        HTTPException: If user doesn't own the resource or other auth error
    """
    logger_instance = get_logger(__name__)
    try:
        await verify_user_ownership(current_user_id, resource_user_id)
        return current_user_id
    except Exception as e:
        # This import should ideally be at the top-level
        from services.user.exceptions import AuthorizationException
        if isinstance(e, AuthorizationException):
            logger_instance.warning(f"User ownership verification failed: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only access your own resources.",
                    "resource": e.resource, # Make sure AuthorizationException has these attributes
                    "action": e.action,
                },
            )
        # Handle other potential exceptions from get_current_user if they are not AuthenticationException
        elif isinstance(e, AuthenticationException): # Should be caught by get_current_user itself
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "AuthenticationError", "message": e.message},
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            logger_instance.error(f"Unexpected ownership verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Or 403 if preferred for general auth failures
                detail={
                    "error": "AuthorizationError", # Or "InternalServerError"
                    "message": "Access verification failed unexpectedly.",
                },
            )
