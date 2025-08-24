"""
Common JWT authentication for Briefly services.

Provides JWT token validation and user extraction that can be reused
across all services to eliminate code duplication.
"""

import time
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.http_errors import AuthError
from services.common.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


def make_verify_jwt_token(get_settings: Callable[[], Any]) -> Callable[[str], Any]:
    """
    Create a JWT verification function that uses the service's settings.

    Args:
        get_settings: Function that returns the service's settings object

    Returns:
        Function that verifies JWT tokens
    """

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
                "Using manual JWT verification "
                "(signature verification potentially disabled based on settings)"
            )

            settings = get_settings()
            verify_signature = getattr(settings, "jwt_verify_signature", True)

            # Get issuer, audience, and JWT key from settings
            issuer = getattr(settings, "nextauth_issuer", "nextauth")
            audience = getattr(settings, "nextauth_audience", None)
            jwt_secret = getattr(settings, "nextauth_jwt_key", None)

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
                # Decode without signature verification but still validate audience
                # if configured
                decoded_token = jwt.decode(
                    token,
                    options={
                        "verify_signature": False,
                        "verify_exp": True,
                        "verify_iat": True,
                        "verify_aud": bool(audience),  # Validate audience if configured
                    },
                    algorithms=["HS256"],
                    audience=(
                        audience if audience else None
                    ),  # Pass audience if configured
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

    return verify_jwt_token


def extract_user_id_from_token(token_claims: Dict[str, Any]) -> str:
    """
    Extract user ID from token claims.

    Args:
        token_claims: Decoded JWT token claims

    Returns:
        User ID as string

    Raises:
        AuthError: If user ID is missing or invalid
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
        User email as string, or None if not present
    """
    email = token_claims.get("email")
    if not email:
        return None

    return str(email)


async def get_current_user_from_gateway_headers(request: Request) -> Optional[str]:
    """
    Get current user ID from gateway headers.

    Args:
        request: FastAPI request object

    Returns:
        User ID from headers, or None if not present
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return None

    logger_instance = get_logger(__name__)
    logger_instance.debug(
        "User authenticated via gateway headers",
        extra={"user_id": user_id},
    )
    return user_id


def make_get_current_user_flexible(
    get_settings: Callable[[], Any],
) -> Callable[[Request, Optional[HTTPAuthorizationCredentials]], Any]:
    """
    Create a flexible authentication function that supports both gateway headers
    and JWT tokens.

    Args:
        get_settings: Function that returns the service's settings object

    Returns:
        Function that handles flexible authentication
    """
    verify_jwt_token = make_verify_jwt_token(get_settings)

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

    return get_current_user_flexible


def make_get_current_user(
    get_settings: Callable[[], Any],
) -> Callable[[Request, Optional[HTTPAuthorizationCredentials]], Any]:
    """
    Create a get_current_user dependency that supports both gateway headers
    and JWT tokens.

    Args:
        get_settings: Function that returns the service's settings object

    Returns:
        FastAPI dependency function
    """
    get_current_user_flexible = make_get_current_user_flexible(get_settings)

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

    return get_current_user


def make_get_current_user_with_claims(
    get_settings: Callable[[], Any],
) -> Callable[[Request, Optional[HTTPAuthorizationCredentials]], Any]:
    """
    Create a get_current_user_with_claims dependency that supports both gateway
    headers and JWT tokens.

    Args:
        get_settings: Function that returns the service's settings object

    Returns:
        FastAPI dependency function
    """
    verify_jwt_token = make_verify_jwt_token(get_settings)

    async def get_current_user_with_claims(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> Dict[str, Any]:
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

    return get_current_user_with_claims


async def verify_user_ownership(current_user_id: str, resource_user_id: str) -> bool:
    """
    Verify that the current user owns the resource.

    Args:
        current_user_id: ID of the authenticated user
        resource_user_id: ID of the user who owns the resource

    Returns:
        True if the current user owns the resource
    """
    return current_user_id == resource_user_id


async def require_user_ownership(current_user_id: str, resource_user_id: str) -> None:
    """
    Require that the current user owns the resource.

    Args:
        current_user_id: ID of the authenticated user
        resource_user_id: ID of the user who owns the resource

    Raises:
        HTTPException: If the current user doesn't own the resource
    """
    if not await verify_user_ownership(current_user_id, resource_user_id):
        raise HTTPException(
            status_code=403, detail="Access denied: you don't own this resource"
        )
