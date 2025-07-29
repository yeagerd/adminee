"""
NextAuth JWT token validation for Shipments Service.

Provides JWT token validation and user extraction.
Handles token verification, decoding, and user information extraction.
Follows the same patterns as the user service authentication.
"""

import logging
import time
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.http_errors import AuthError
from services.common.logging_config import get_logger
from services.shipments.settings import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token using manual verification.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token claims (mixed types - timestamps remain numeric)

    Raises:
        AuthError: If token is invalid
    """
    logger_instance = get_logger(__name__)

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
            # Decode without signature verification but still validate audience if configured
            decoded_token = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": bool(audience),  # Validate audience if configured
                },
                algorithms=["HS256"],
                audience=audience if audience else None,  # Pass audience if configured
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

    except jwt.ExpiredSignatureError:
        logger_instance.warning("Token expired")
        raise AuthError("Token expired")
    except jwt.InvalidTokenError as e:
        logger_instance.warning(f"Invalid token: {e}")
        raise AuthError("Invalid token")
    except Exception as e:
        logger_instance.error(f"Unexpected JWT verification error: {e}")
        raise AuthError("Token verification failed")


def extract_user_id_from_token(token_claims: Dict[str, Any]) -> str:
    """
    Extract user ID from token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User ID as string

    Raises:
        AuthError: If user ID cannot be extracted
    """
    user_id = token_claims.get("sub")
    if not user_id:
        raise AuthError("Missing user ID in token")
    return str(user_id)


def extract_user_email_from_token(token_claims: Dict[str, Any]) -> Optional[str]:
    """
    Extract user email from token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User email or None if not present
    """
    return token_claims.get("email")


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
) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate current user with full token claims.

    This function supports both gateway headers and JWT tokens for authentication.
    For gateway headers, it returns minimal claims. For JWT tokens, it returns
    the full decoded token claims.

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
            "sub": str(user_id),
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