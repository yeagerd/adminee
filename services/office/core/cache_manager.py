"""
Cache manager for the Office Service using Redis.
Provides async methods for caching API responses with TTL support.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from services.office.core.settings import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based cache manager for the Office Service.

    Provides async methods for caching API responses and other data with TTL support.
    """

    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._connection_lock = asyncio.Lock()

    async def _get_redis(self) -> Redis:
        """Get Redis connection with lazy initialization."""
        if self._redis is None:
            async with self._connection_lock:
                if self._redis is None:
                    try:
                        self._redis = redis.from_url(
                            get_settings().REDIS_URL,
                            encoding="utf-8",
                            decode_responses=True,
                            socket_timeout=5.0,
                            socket_connect_timeout=5.0,
                            retry_on_timeout=True,
                        )
                        # Test connection
                        await self._redis.ping()
                        logger.info("Redis connection established successfully")
                    except Exception as e:
                        logger.error(f"Failed to connect to Redis: {e}")
                        raise
        return self._redis

    async def get_from_cache(self, key: str) -> Optional[Any]:
        """
        Retrieve data from cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached data if exists, None otherwise
        """
        try:
            redis_client = await self._get_redis()
            cached_data = await redis_client.get(key)

            if cached_data is None:
                logger.debug(f"Cache miss for key: {key}")
                return None

            # Deserialize JSON data
            data = json.loads(cached_data)
            logger.debug(f"Cache hit for key: {key}")
            return data

        except Exception as e:
            logger.error(f"Failed to get data from cache for key '{key}': {e}")
            return None

    async def set_to_cache(
        self, key: str, data: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store data in cache with optional TTL.

        Args:
            key: Cache key to store under
            data: Data to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds (defaults to settings.DEFAULT_CACHE_TTL_SECONDS)

        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self._get_redis()

            # Serialize data to JSON
            serialized_data = json.dumps(data, default=self._json_serializer)

            # Use default TTL if not specified
            if ttl_seconds is None:
                ttl_seconds = get_settings().CACHE_TTL

            # Set data with TTL
            await redis_client.setex(key, ttl_seconds, serialized_data)

            logger.debug(f"Cached data for key: {key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to set data to cache for key '{key}': {e}")
            return False

    async def delete_from_cache(self, key: str) -> bool:
        """
        Delete data from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            deleted_count = await redis_client.delete(key)

            if deleted_count > 0:
                logger.debug(f"Deleted cache key: {key}")
                return True
            else:
                logger.debug(f"Cache key not found for deletion: {key}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete cache key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all cache keys matching a pattern.

        Args:
            pattern: Redis pattern to match (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys(pattern)

            if not keys:
                logger.debug(f"No keys found matching pattern: {pattern}")
                return 0

            deleted_count = await redis_client.delete(*keys)
            logger.debug(f"Deleted {deleted_count} keys matching pattern: {pattern}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete keys matching pattern '{pattern}': {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a cache key exists.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            exists_count = await redis_client.exists(key)
            return exists_count > 0

        except Exception as e:
            logger.error(f"Failed to check existence of cache key '{key}': {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL for a cache key.

        Args:
            key: Cache key to check

        Returns:
            TTL in seconds, None if key doesn't exist or has no expiry
        """
        try:
            redis_client = await self._get_redis()
            ttl = await redis_client.ttl(key)

            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but has no expiry
                return None
            else:
                return ttl

        except Exception as e:
            logger.error(f"Failed to get TTL for cache key '{key}': {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def generate_cache_key(
    user_id: str, provider: str, endpoint: str, params: Dict[str, Any]
) -> str:
    """
    Generate consistent cache keys for Office Service data.

    This function creates deterministic cache keys based on user ID, provider,
    endpoint, and request parameters to ensure consistent caching behavior.

    Args:
        user_id: ID of the user making the request
        provider: Provider name (google, microsoft)
        endpoint: API endpoint being cached (e.g., "messages", "events")
        params: Request parameters dictionary

    Returns:
        Generated cache key string

    Examples:
        >>> generate_cache_key("user123", "google", "messages", {"limit": 10})
        'office_service:user123:google:messages:5d41402abc4b2a76b9719d911017c592'
    """
    # Sort parameters to ensure consistent ordering
    sorted_params = dict(sorted(params.items()))

    # Create hash of parameters
    param_string = json.dumps(sorted_params, sort_keys=True, separators=(",", ":"))
    param_hash = hashlib.md5(param_string.encode()).hexdigest()

    # Generate cache key
    cache_key = f"office_service:{user_id}:{provider}:{endpoint}:{param_hash}"

    return cache_key


def generate_user_cache_pattern(user_id: str, provider: Optional[str] = None) -> str:
    """
    Generate a cache pattern for deleting all user data.

    Args:
        user_id: User ID
        provider: Optional provider filter

    Returns:
        Cache pattern string
    """
    if provider:
        return f"office:{user_id}:{provider}:*"
    return f"office:{user_id}:*"


def generate_thread_cache_key(
    user_id: str,
    thread_id: Optional[str] = None,
    include_body: bool = False,
    **kwargs: Any,
) -> str:
    """
    Generate a cache key for thread-related data.

    Args:
        user_id: User ID
        thread_id: Optional specific thread ID
        include_body: Whether body content is included
        **kwargs: Additional parameters for cache key

    Returns:
        Cache key string
    """
    key_parts = ["office", user_id, "thread"]

    if thread_id:
        key_parts.append(thread_id)

    if include_body:
        key_parts.append("with_body")

    # Add additional parameters
    for key, value in sorted(kwargs.items()):
        if value is not None:
            key_parts.extend([key, str(value)])

    return ":".join(key_parts)


def generate_threads_list_cache_key(
    user_id: str,
    providers: Optional[List[str]] = None,
    limit: Optional[int] = None,
    include_body: bool = False,
    labels: Optional[List[str]] = None,
    folder_id: Optional[str] = None,
    q: Optional[str] = None,
    page_token: Optional[str] = None,
) -> str:
    """
    Generate a cache key for threads list data.

    Args:
        user_id: User ID
        providers: List of providers
        limit: Maximum number of threads
        include_body: Whether body content is included
        labels: Filter by labels
        folder_id: Folder ID filter
        q: Search query
        page_token: Pagination token

    Returns:
        Cache key string
    """
    key_parts = ["office", user_id, "threads"]

    if providers:
        key_parts.extend(["providers", ",".join(sorted(providers))])

    if limit:
        key_parts.extend(["limit", str(limit)])

    if include_body:
        key_parts.append("with_body")

    if labels:
        key_parts.extend(["labels", ",".join(sorted(labels))])

    if folder_id:
        key_parts.extend(["folder", folder_id])

    if q:
        key_parts.extend(["q", q])

    if page_token:
        key_parts.extend(["page", page_token])

    return ":".join(key_parts)


def generate_message_thread_cache_key(
    user_id: str,
    message_id: str,
    include_body: bool = False,
) -> str:
    """
    Generate a cache key for message thread data.

    Args:
        user_id: User ID
        message_id: Message ID
        include_body: Whether body content is included

    Returns:
        Cache key string
    """
    key_parts = ["office", user_id, "message_thread", message_id]

    if include_body:
        key_parts.append("with_body")

    return ":".join(key_parts)


def generate_thread_cache_pattern(user_id: str, provider: Optional[str] = None) -> str:
    """
    Generate a cache pattern for deleting all thread data for a user.

    Args:
        user_id: User ID
        provider: Optional provider filter

    Returns:
        Cache pattern string
    """
    if provider:
        return f"office:{user_id}:thread:{provider}:*"
    return f"office:{user_id}:thread*"


# Global cache manager instance
cache_manager = CacheManager()
