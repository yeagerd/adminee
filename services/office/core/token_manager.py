"""
Token Management module for the Office Service.

This module handles secure retrieval and caching of OAuth tokens from the User
Management Service. It provides thread-safe in-memory caching with TTL to reduce
API calls and improve performance while maintaining security best practices.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from services.common.logging_config import get_logger
from services.office.core.settings import get_settings

# Configure logging
logger = get_logger(__name__)


class TokenData(BaseModel):
    """Token data model for storing retrieved tokens"""

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = []
    provider: str
    user_id: str
    success: bool = True
    error: Optional[str] = None


class CachedToken:
    """Internal class for storing cached tokens with TTL"""

    def __init__(
        self, token_data: TokenData, ttl_seconds: int = 900
    ):  # 15 minutes default
        self.token_data = token_data
        self.cache_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=ttl_seconds
        )

    def is_expired(self) -> bool:
        """Check if either the cache TTL or the actual token has expired"""
        now = datetime.now(timezone.utc)

        # Check cache TTL expiration
        if now > self.cache_expires_at:
            return True

        # Check actual token expiration if available
        if self.token_data.expires_at:
            # Ensure expires_at is timezone-aware for comparison
            token_expires_at = self.token_data.expires_at
            if token_expires_at.tzinfo is None:
                token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

            # Add a small buffer (5 minutes) to refresh tokens before they actually expire
            buffer_time = timedelta(minutes=5)
            if now + buffer_time >= token_expires_at:
                return True

        return False


class TokenManager:
    """
    Manages token retrieval from User Management Service with caching and error handling.

    Features:
    - Async token retrieval from User Management Service
    - In-memory token caching with TTL
    - Robust error handling and logging
    - httpx.AsyncClient integration
    """

    def __init__(self) -> None:
        self.http_client: Optional[httpx.AsyncClient] = None
        self._token_cache: Dict[str, CachedToken] = {}
        self._cache_lock = asyncio.Lock()
        self._client_lock = asyncio.Lock()
        self._client_ref_count = 0
        # Add instance tracking
        self._instance_id = str(uuid.uuid4())[:8]
        logger.info(f"TokenManager instance created: {self._instance_id}")

    async def __aenter__(self) -> "TokenManager":
        """Async context manager entry"""
        async with self._client_lock:
            self._client_ref_count += 1
            logger.info(
                f"TokenManager instance {self._instance_id}: Client ref count increased to {self._client_ref_count}"
            )

            # Only initialize if this is the first user
            if self._client_ref_count == 1:
                try:

                    # Use API key for user management service if available
                    headers: dict[str, str] = {}
                    api_key = get_settings().api_office_user_key
                    if api_key:
                        headers["X-API-Key"] = api_key

                    # Note: We don't set X-Request-Id here anymore since it should be per-request
                    # The request ID will be set dynamically in get_user_token for each request

                    self.http_client = httpx.AsyncClient(
                        timeout=httpx.Timeout(10.0),  # 10 second timeout
                        headers=headers,
                    )
                    logger.info(
                        f"TokenManager instance {self._instance_id} initialized successfully"
                    )
                except Exception as e:
                    # If initialization fails, decrement the ref count and re-raise
                    self._client_ref_count -= 1
                    logger.error(
                        f"TokenManager instance {self._instance_id} initialization failed: {e}"
                    )
                    raise

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        async with self._client_lock:
            self._client_ref_count -= 1
            logger.info(
                f"TokenManager instance {self._instance_id}: Client ref count decreased to {self._client_ref_count}"
            )

            # Only close if this is the last user
            if self._client_ref_count == 0:
                if self.http_client:
                    await self.http_client.aclose()
                    self.http_client = None
                    logger.info(f"TokenManager instance {self._instance_id} closed")
            elif self._client_ref_count < 0:
                logger.warning(
                    f"TokenManager instance {self._instance_id}: Negative ref count detected: {self._client_ref_count}"
                )
                self._client_ref_count = 0

    def _generate_cache_key(
        self, user_id: str, provider: str, scopes: List[str]
    ) -> str:
        """Generate cache key for token storage"""
        # Sort scopes for consistent key generation
        sorted_scopes = sorted(scopes)
        scopes_str = ",".join(sorted_scopes)
        return f"token:{user_id}:{provider}:{scopes_str}"

    async def _get_from_cache(self, cache_key: str) -> Optional[TokenData]:
        """Retrieve token from cache if not expired"""
        async with self._cache_lock:
            cached_token = self._token_cache.get(cache_key)
            if cached_token:
                if not cached_token.is_expired():
                    logger.debug(f"Cache hit for token: {cache_key}")
                    return cached_token.token_data
                else:
                    # Log why the token was considered expired
                    now = datetime.now(timezone.utc)
                    if now > cached_token.cache_expires_at:
                        logger.debug(
                            f"Removed token from cache due to TTL expiration: {cache_key}"
                        )
                    elif cached_token.token_data.expires_at:
                        token_expires_at = cached_token.token_data.expires_at
                        if token_expires_at.tzinfo is None:
                            token_expires_at = token_expires_at.replace(
                                tzinfo=timezone.utc
                            )
                        buffer_time = timedelta(minutes=5)
                        if now + buffer_time >= token_expires_at:
                            logger.debug(
                                f"Removed token from cache due to token expiration (with buffer): {cache_key}"
                            )

                    # Remove expired token
                    del self._token_cache[cache_key]
            return None

    async def _set_cache(
        self, cache_key: str, token_data: TokenData, ttl_seconds: int = 900
    ) -> None:
        """Store token in cache with TTL"""
        async with self._cache_lock:
            self._token_cache[cache_key] = CachedToken(token_data, ttl_seconds)
            logger.debug(f"Cached token: {cache_key}")

    async def _cleanup_expired_tokens(self) -> None:
        """Remove all expired tokens from cache"""
        async with self._cache_lock:
            expired_keys = [
                key
                for key, cached_token in self._token_cache.items()
                if cached_token.is_expired()
            ]
            for key in expired_keys:
                del self._token_cache[key]
            if expired_keys:
                logger.debug(
                    f"Cleaned up {len(expired_keys)} expired tokens from cache"
                )

    async def get_user_token(
        self, user_id: str, provider: str, scopes: List[str]
    ) -> Optional[TokenData]:
        """
        Retrieve valid token from User Management Service with caching.

        Args:
            user_id: The user ID to get the token for
            provider: Provider name (google, microsoft)
            scopes: List of required OAuth scopes

        Returns:
            TokenData object if successful, None if failed
        """
        # Check cache first
        cache_key = self._generate_cache_key(user_id, provider, scopes)
        cached_token = await self._get_from_cache(cache_key)
        if cached_token:
            logger.info(
                f"TokenManager instance {self._instance_id}: Cache HIT for user {user_id}, provider {provider}"
            )
            return cached_token

        logger.info(
            f"TokenManager instance {self._instance_id}: Cache MISS for user {user_id}, provider {provider}"
        )

        # Clean up expired tokens periodically
        await self._cleanup_expired_tokens()

        if not self.http_client:
            logger.error("TokenManager not initialized. Use async context manager.")
            return None

        try:
            logger.info(
                f"TokenManager instance {self._instance_id}: Requesting token for user {user_id}, provider {provider}"
            )

            # Get current request ID for distributed tracing
            from services.common.logging_config import request_id_var

            request_id = request_id_var.get()

            # Prepare headers with dynamic request ID and API key authentication
            headers = {}
            if request_id and request_id != "uninitialized":
                headers["X-Request-Id"] = request_id

            # Add API key authentication for service-to-service communication
            api_key = get_settings().api_office_user_key
            if api_key:
                headers["X-API-Key"] = api_key
            else:
                logger.warning(
                    f"TokenManager instance {self._instance_id}: No API key configured for user service communication"
                )

            response = await self.http_client.post(
                f"{get_settings().USER_SERVICE_URL}/v1/internal/tokens/get",
                json={
                    "user_id": user_id,
                    "provider": provider,
                    "required_scopes": scopes,
                },
                headers=headers,
            )

            if response.status_code == 200:
                response_data = response.json()

                # Check if the response indicates success
                if response_data.get("success", False):
                    token_data = TokenData(**response_data)

                    # Cache the token
                    await self._set_cache(cache_key, token_data)

                    logger.info(
                        f"TokenManager instance {self._instance_id}: Successfully retrieved and cached token for user {user_id}, provider {provider}"
                    )
                    return token_data
                else:
                    # Log the error from the User service
                    error_msg = response_data.get("error", "Unknown error")
                    logger.warning(
                        f"TokenManager instance {self._instance_id}: Token retrieval failed for user {user_id}, provider {provider}: {error_msg}"
                    )
                    return None

            elif response.status_code == 404:
                logger.warning(
                    f"TokenManager instance {self._instance_id}: No token found for user {user_id}, provider {provider}"
                )
                return None

            elif response.status_code == 403:
                logger.warning(
                    f"TokenManager instance {self._instance_id}: Insufficient permissions for user {user_id}, provider {provider}"
                )
                return None

            else:
                logger.error(
                    f"TokenManager instance {self._instance_id}: Token retrieval failed with status {response.status_code}: {response.text}"
                )
                return None

        except httpx.TimeoutException:
            logger.error(
                f"TokenManager instance {self._instance_id}: Token retrieval timed out for user {user_id}, provider {provider}"
            )
            return None

        except httpx.NetworkError as e:
            logger.error(
                f"TokenManager instance {self._instance_id}: Network error during token retrieval for user {user_id}, provider {provider}: {e}"
            )
            return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f"TokenManager instance {self._instance_id}: HTTP error during token retrieval for user {user_id}, provider {provider}: {e}"
            )
            return None

        except Exception as e:
            logger.error(
                f"TokenManager instance {self._instance_id}: Unexpected error during token retrieval for user {user_id}, provider {provider}: {e}"
            )
            return None

    async def invalidate_cache(
        self, user_id: str, provider: Optional[str] = None
    ) -> None:
        """
        Invalidate cached tokens for a user.

        Args:
            user_id: User ID to invalidate tokens for
            provider: Optional provider name. If None, invalidates all providers for the user
        """
        async with self._cache_lock:
            keys_to_remove = []
            for key in self._token_cache.keys():
                if provider:
                    if key.startswith(f"token:{user_id}:{provider}:"):
                        keys_to_remove.append(key)
                else:
                    if key.startswith(f"token:{user_id}:"):
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._token_cache[key]

            logger.info(
                f"Invalidated {len(keys_to_remove)} cached tokens for user {user_id}"
            )

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        total_tokens = len(self._token_cache)
        expired_tokens = sum(
            1
            for cached_token in self._token_cache.values()
            if cached_token.is_expired()
        )
        active_tokens = total_tokens - expired_tokens

        return {
            "total_cached_tokens": total_tokens,
            "active_tokens": active_tokens,
            "expired_tokens": expired_tokens,
        }
