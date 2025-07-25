"""
Token Management module for the Office Service.

This module handles secure retrieval and caching of OAuth tokens from the User
Management Service. It provides thread-safe in-memory caching with TTL to reduce
API calls and improve performance while maintaining security best practices.
"""

import asyncio
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
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


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

    async def __aenter__(self) -> "TokenManager":
        """Async context manager entry"""
        from services.common.logging_config import request_id_var

        # Use API key for user management service if available
        headers: dict[str, str] = {}
        api_key = get_settings().api_office_user_key
        if api_key:
            headers["X-API-Key"] = api_key

        # Propagate request ID for distributed tracing
        request_id = request_id_var.get()
        if request_id and request_id != "uninitialized":
            headers["X-Request-Id"] = request_id

        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),  # 10 second timeout
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()

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
            if cached_token and not cached_token.is_expired():
                logger.debug(f"Cache hit for token: {cache_key}")
                return cached_token.token_data
            elif cached_token:
                # Remove expired token
                del self._token_cache[cache_key]
                logger.debug(f"Removed expired token from cache: {cache_key}")
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
            return cached_token

        # Clean up expired tokens periodically
        await self._cleanup_expired_tokens()

        if not self.http_client:
            logger.error("TokenManager not initialized. Use async context manager.")
            return None

        try:
            logger.info(f"Requesting token for user {user_id}, provider {provider}")

            response = await self.http_client.post(
                f"{get_settings().USER_MANAGEMENT_SERVICE_URL}/v1/internal/tokens/get",
                json={
                    "user_id": user_id,
                    "provider": provider,
                    "required_scopes": scopes,
                },
            )

            if response.status_code == 200:
                response_data = response.json()

                # Check if the response indicates success
                if response_data.get("success", False):
                    token_data = TokenData(**response_data)

                    # Cache the token
                    await self._set_cache(cache_key, token_data)

                    logger.info(
                        f"Successfully retrieved token for user {user_id}, provider {provider}"
                    )
                    return token_data
                else:
                    # Log the error from the User service
                    error_msg = response_data.get("error", "Unknown error")
                    logger.warning(
                        f"Token retrieval failed for user {user_id}, provider {provider}: {error_msg}"
                    )
                    return None

            elif response.status_code == 404:
                logger.warning(
                    f"No token found for user {user_id}, provider {provider}"
                )
                return None

            elif response.status_code == 403:
                logger.warning(
                    f"Insufficient permissions for user {user_id}, provider {provider}"
                )
                return None

            else:
                logger.error(
                    f"Token retrieval failed with status {response.status_code}: {response.text}"
                )
                return None

        except httpx.TimeoutException:
            logger.error(
                f"Token retrieval timed out for user {user_id}, provider {provider}"
            )
            return None

        except httpx.NetworkError as e:
            logger.error(
                f"Network error during token retrieval for user {user_id}, provider {provider}: {e}"
            )
            return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error during token retrieval for user {user_id}, provider {provider}: {e}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Unexpected error during token retrieval for user {user_id}, provider {provider}: {e}"
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
