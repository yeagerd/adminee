import redis.asyncio as redis # Use asyncio version of redis for FastAPI
import json
import hashlib
import logging
from typing import Optional, Dict, Any

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global Redis connection pool instance
redis_pool: Optional[redis.Redis] = None

async def init_redis_pool():
    global redis_pool
    if not redis_pool:
        try:
            redis_pool = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True # Important for getting strings back directly
            )
            # Test connection
            await redis_pool.ping()
            logger.info("Successfully connected to Redis and initialized connection pool.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            redis_pool = None # Set to None if connection fails

async def get_redis_connection() -> Optional[redis.Redis]:
    if not redis_pool:
        # This might happen if init_redis_pool failed or was not called during startup.
        # Optionally, try to initialize again, or just log the issue.
        logger.warning("Redis pool not initialized. Attempting to initialize now.")
        await init_redis_pool()
    return redis_pool

async def close_redis_pool():
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        logger.info("Redis connection pool closed.")
        redis_pool = None

def generate_cache_key(
    user_id: str,
    endpoint: str, # Changed from provider: Optional[str] to reflect usage better
    provider: Optional[str] = None, # Provider can still be part of the key if needed
    params: Optional[Dict[str, Any]] = None
) -> str:
    # Sort params for consistency
    param_str = json.dumps(params, sort_keys=True) if params else ""
    # Include provider in the key if it's provided
    provider_part = f":{provider}" if provider else ""

    # Create a hash of the params to keep the key length manageable
    param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()

    key = f"office_service:{user_id}{provider_part}:{endpoint}:{param_hash}"
    logger.debug(f"Generated cache key: {key} for user_id={user_id}, provider={provider}, endpoint={endpoint}, params_hash={param_hash}")
    return key

async def get_from_cache(key: str) -> Optional[Any]:
    redis_client = await get_redis_connection()
    if not redis_client:
        logger.error(f"Cannot get from cache: Redis client not available. Key: {key}")
        return None
    try:
        cached_value = await redis_client.get(key)
        if cached_value:
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(cached_value) # Deserialize JSON
        logger.debug(f"Cache miss for key: {key}")
        return None
    except Exception as e:
        logger.error(f"Error getting value from cache for key {key}: {e}", exc_info=True)
        return None

async def set_to_cache(key: str, value: Any, ttl_seconds: Optional[int] = None):
    redis_client = await get_redis_connection()
    if not redis_client:
        logger.error(f"Cannot set to cache: Redis client not available. Key: {key}")
        return

    try:
        serialized_value = json.dumps(value) # Serialize to JSON string

        # Use default TTL from settings if not provided
        actual_ttl = ttl_seconds if ttl_seconds is not None else settings.DEFAULT_CACHE_TTL_SECONDS

        await redis_client.set(key, serialized_value, ex=actual_ttl)
        logger.debug(f"Set value to cache for key: {key} with TTL: {actual_ttl}s")
    except Exception as e:
        logger.error(f"Error setting value to cache for key {key}: {e}", exc_info=True)

async def delete_from_cache(key: str) -> bool:
    redis_client = await get_redis_connection()
    if not redis_client:
        logger.error(f"Cannot delete from cache: Redis client not available. Key: {key}")
        return False
    try:
        result = await redis_client.delete(key)
        logger.debug(f"Deleted key {key} from cache, result: {result}")
        return result > 0 # delete returns number of keys deleted
    except Exception as e:
        logger.error(f"Error deleting value from cache for key {key}: {e}", exc_info=True)
        return False
