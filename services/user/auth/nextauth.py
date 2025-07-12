"""
NextAuth JWT token validation for User Management Service.

Provides JWT token validation and user extraction.
Handles token verification, decoding, and user information extraction.
"""

import logging
import time
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.http_errors import AuthError
from services.user.logging_config import get_logger
from services.user.settings import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def verify_jwt_token(token: str) -> Dict[str, str]:
    """
    Verify JWT token using manual verification.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token claims

    Raises:
        AuthError: If token is invalid
    """
    logger_instance = get_logger(__name__)  # Use a local logger instance

    try:
        logger_instance.info(
            "Using manual JWT verification (signature verification potentially disabled based on settings)"
        )

        settings = get_settings()
        verify_signature = getattr(settings, "jwt_verify_signature", True)

        # Get issuer, audience, and JWT key from settings
        issuer = getattr(settings, "nextauth_issuer", "nextauth")
        audience = getattr(settings, "nextauth_audience")
        jwt_secret = getattr(settings, "nextauth_jwt_key")

        if verify_signature and jwt_secret:
            # Verify signature with secret
            decoded_token = jwt.decode(
                token,
                key=str(jwt_secret),
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": bool(audience),
                },
                algorithms=["HS256"],  # NextAuth uses HS256 by default
                issuer=issuer,
                audience=audience if audience else None,
            )
        elif not verify_signature:
            # Decode without signature verification
            decoded_token = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,
                },
                algorithms=["HS256"],
            )
        else:
            # Signature verification is required but no secret is configured
            logger_instance.error("JWT verification configuration error")
            raise AuthError("JWT verification configuration error")

        # Validate required claims
        required_claims = ["sub", "iss", "exp", "iat"]
        for claim in required_claims:
            if claim not in decoded_token:
                logger_instance.error(f"Missing required claim: {claim}")
                raise AuthError(f"Missing required claim: {claim}")

        logger_instance.info(
            "Token validated successfully",
            extra={
                "user_id": decoded_token.get("sub"),
                "issuer": decoded_token.get("iss"),
            },
        )

        return decoded_token

    except AuthError:
        raise
    except jwt.ExpiredSignatureError:
        logger_instance.warning("JWT token has expired")
        raise AuthError("Token has expired")

    except jwt.InvalidTokenError as e:
        logger_instance.warning(f"Invalid JWT token: {e}")
        raise AuthError("Invalid token")

    except Exception as e:
        logger_instance.error(f"Token verification failed: {e}")
        raise AuthError("Token verification failed")


def extract_user_id_from_token(token_claims: Dict[str, str]) -> str:
    """
    Extract user ID ('sub' claim) from validated JWT token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User ID from token

    Raises:
        AuthError: If user ID cannot be extracted
    """
    user_id = token_claims.get("sub")
    if not user_id:
        raise AuthError("User ID not found in token")

    return user_id


def extract_user_email_from_token(token_claims: Dict[str, str]) -> Optional[str]:
    """
    Extract user email from validated JWT token claims.
    NextAuth stores email in 'email' claim.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User email from token or None if not present
    """
    # NextAuth stores email in 'email' claim
    # It may also be present in the 'user' object if using a custom session callback
    email = token_claims.get("email")
    if not email and "user" in token_claims and isinstance(token_claims["user"], dict):
        email = token_claims["user"].get("email")

    return email


def validate_token_permissions(
    token_claims: Dict[str, str], required_permissions: Optional[list] = None
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
    if required_permissions is None:
        required_permissions = []
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
                    "present": list(token_permissions),
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
    if exp_timestamp is None:  # No expiration claim, treat as problematic or expired
        return True
    return time.time() >= int(exp_timestamp)


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
    logger_instance = get_logger(__name__)

    # Check for gateway headers
    user_id = request.headers.get("X-User-Id")
    if user_id:
        logger_instance.debug(
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
    logger_instance = get_logger(__name__)

    # First try gateway headers
    user_id = await get_current_user_from_gateway_headers(request)
    if user_id:
        return user_id

    # Fall back to JWT token if no gateway headers
    if not credentials:
        logger_instance.warning("No authentication credentials provided")
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        token_claims = await verify_jwt_token(credentials.credentials)
        user_id = extract_user_id_from_token(token_claims)
        logger_instance.debug(
            "User authenticated via JWT token", extra={"user_id": user_id}
        )
        return user_id
    except AuthError as e:
        logger_instance.warning(f"JWT authentication failed: {e.message}")
        raise HTTPException(status_code=401, detail=e.message)
    except Exception as e:
        logger_instance.error(f"Unexpected JWT authentication error: {e}")
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


async def get_current_user_with_claims(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, str]:
    """
    FastAPI dependency to extract current user's full token claims.

    This function supports both gateway headers and JWT tokens for authentication.
    When using gateway headers, it returns a minimal claims object with the user ID.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token credentials (optional)

    Returns:
        Full token claims dictionary or minimal claims from gateway headers

    Raises:
        HTTPException: If authentication fails
    """
    logger_instance = get_logger(__name__)

    # First try gateway headers
    user_id = await get_current_user_from_gateway_headers(request)
    if user_id:
        # Return minimal claims object for gateway authentication
        claims = {
            "sub": user_id,
            "iss": "gateway",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour from now
        }
        logger_instance.debug(
            "User authenticated with gateway headers",
            extra={"user_id": user_id},
        )
        return claims

    # Fall back to JWT token if no gateway headers
    if not credentials:
        logger_instance.warning("No authentication credentials provided")
        raise AuthError(message="Authentication required")

    try:
        token_claims = await verify_jwt_token(credentials.credentials)
        logger_instance.debug(
            "User authenticated with JWT claims",
            extra={"user_id": token_claims.get("sub")},
        )
        return token_claims
    except AuthError as e:
        logger_instance.warning(f"JWT authentication failed: {e.message}")
        raise AuthError(message=e.message)
    except Exception as e:
        logger_instance.error(f"Unexpected JWT authentication error: {e}")
        raise AuthError(message="Authentication failed")


async def verify_user_ownership(current_user_id: str, resource_user_id: str) -> bool:
    """
    Verify that the current user owns the resource being accessed.

    Args:
        current_user_id: ID of the currently authenticated user
        resource_user_id: User ID associated with the resource

    Returns:
        True if user owns the resource

    Raises:
        HTTPException: If user doesn't own the resource
    """
    logger_instance = get_logger(__name__)
    if current_user_id != resource_user_id:
        logger_instance.warning(
            f"User {current_user_id} attempted to access resource owned by {resource_user_id}"
        )
        raise HTTPException(status_code=403, detail="User does not own the resource.")
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
    except HTTPException as e:
        logger_instance.warning(f"User ownership verification failed: {e.detail}")
        raise
    except Exception as e:
        logger_instance.error(f"Unexpected ownership verification error: {e}")
        raise HTTPException(status_code=403, detail="Access verification failed")
