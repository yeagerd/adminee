"""
Redis reference pattern for managing large payloads and idempotency keys.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class RedisReferencePattern:
    """Redis reference pattern for managing large payloads and idempotency."""

    # Key patterns for different data types
    KEY_PATTERNS = {
        "office": "office:{user_id}:{doc_type}:{doc_id}",
        "email": "email:{user_id}:{provider}:{doc_id}",
        "calendar": "calendar:{user_id}:{provider}:{doc_id}",
        "contact": "contact:{user_id}:{provider}:{doc_id}",
        "document": "document:{user_id}:{provider}:{doc_id}",
        "todo": "todo:{user_id}:{provider}:{doc_id}",
        "idempotency": "idempotency:{key}",
        "batch": "batch:{batch_id}:{correlation_id}",
        "fragment": "fragment:{parent_doc_id}:{fragment_id}",
    }

    # TTL settings for different data types (in seconds)
    TTL_SETTINGS = {
        "office": 86400 * 7,  # 7 days
        "email": 86400 * 30,  # 30 days
        "calendar": 86400 * 30,  # 30 days
        "contact": 86400 * 90,  # 90 days
        "document": 86400 * 365,  # 1 year
        "todo": 86400 * 90,  # 90 days
        "idempotency": 86400,  # 24 hours
        "batch": 86400 * 3,  # 3 days
        "fragment": 86400 * 365,  # 1 year
    }

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    def store_large_payload(
        self,
        data_type: str,
        user_id: str,
        doc_id: str,
        payload: Dict[str, Any],
        provider: Optional[str] = None,
        ttl_override: Optional[int] = None,
    ) -> str:
        """Store a large payload in Redis and return a reference key."""
        try:
            # Generate the Redis key
            if data_type == "office":
                redis_key = self.KEY_PATTERNS[data_type].format(
                    user_id=user_id,
                    doc_type=payload.get("type", "unknown"),
                    doc_id=doc_id,
                )
            elif data_type in ["email", "calendar", "contact", "document", "todo"]:
                if not provider:
                    raise ValueError(f"Provider is required for {data_type} data type")
                redis_key = self.KEY_PATTERNS[data_type].format(
                    user_id=user_id, provider=provider, doc_id=doc_id
                )
            else:
                # Fallback to generic pattern
                redis_key = f"{data_type}:{user_id}:{doc_id}"

            # Serialize the payload
            serialized_payload = json.dumps(payload, default=self._json_serializer)

            # Store in Redis with TTL
            ttl = ttl_override or self.TTL_SETTINGS.get(data_type, 86400)
            self.redis.setex(redis_key, ttl, serialized_payload)

            logger.info(f"Stored large payload in Redis: {redis_key} (TTL: {ttl}s)")
            return redis_key

        except Exception as e:
            logger.error(f"Error storing large payload in Redis: {e}")
            raise

    def retrieve_large_payload(self, redis_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a large payload from Redis using the reference key."""
        try:
            payload_data = self.redis.get(redis_key)
            if payload_data:
                payload = json.loads(payload_data)
                logger.debug(f"Retrieved large payload from Redis: {redis_key}")
                return payload
            else:
                logger.warning(f"Payload not found in Redis: {redis_key}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving large payload from Redis: {e}")
            return None

    def store_idempotency_key(
        self, key: str, metadata: Dict[str, Any], ttl_override: Optional[int] = None
    ) -> bool:
        """Store an idempotency key with metadata in Redis."""
        try:
            redis_key = self.KEY_PATTERNS["idempotency"].format(key=key)

            # Add timestamp to metadata
            metadata["stored_at"] = datetime.utcnow().isoformat()
            metadata["key"] = key

            # Serialize metadata
            serialized_metadata = json.dumps(metadata, default=self._json_serializer)

            # Store in Redis with TTL
            ttl = ttl_override or self.TTL_SETTINGS["idempotency"]
            result = self.redis.setex(redis_key, ttl, serialized_metadata)

            if result:
                logger.info(f"Stored idempotency key in Redis: {key} (TTL: {ttl}s)")
                return True
            else:
                logger.warning(f"Failed to store idempotency key in Redis: {key}")
                return False

        except Exception as e:
            logger.error(f"Error storing idempotency key in Redis: {e}")
            return False

    def check_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Check if an idempotency key exists and return its metadata."""
        try:
            redis_key = self.KEY_PATTERNS["idempotency"].format(key=key)
            metadata_data = self.redis.get(redis_key)

            if metadata_data:
                metadata = json.loads(metadata_data)
                logger.debug(f"Found idempotency key in Redis: {key}")
                return metadata
            else:
                logger.debug(f"Idempotency key not found in Redis: {key}")
                return None

        except Exception as e:
            logger.error(f"Error checking idempotency key in Redis: {e}")
            return None

    def store_batch_reference(
        self,
        batch_id: str,
        correlation_id: str,
        batch_data: Dict[str, Any],
        ttl_override: Optional[int] = None,
    ) -> str:
        """Store batch operation reference in Redis."""
        try:
            redis_key = self.KEY_PATTERNS["batch"].format(
                batch_id=batch_id, correlation_id=correlation_id
            )

            # Add metadata
            batch_data["batch_id"] = batch_id
            batch_data["correlation_id"] = correlation_id
            batch_data["stored_at"] = datetime.utcnow().isoformat()

            # Serialize batch data
            serialized_data = json.dumps(batch_data, default=self._json_serializer)

            # Store in Redis with TTL
            ttl = ttl_override or self.TTL_SETTINGS["batch"]
            self.redis.setex(redis_key, ttl, serialized_data)

            logger.info(f"Stored batch reference in Redis: {redis_key} (TTL: {ttl}s)")
            return redis_key

        except Exception as e:
            logger.error(f"Error storing batch reference in Redis: {e}")
            raise

    def retrieve_batch_reference(
        self, batch_id: str, correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve batch operation reference from Redis."""
        try:
            redis_key = self.KEY_PATTERNS["batch"].format(
                batch_id=batch_id, correlation_id=correlation_id
            )

            batch_data = self.redis.get(redis_key)
            if batch_data:
                data = json.loads(batch_data)
                logger.debug(f"Retrieved batch reference from Redis: {redis_key}")
                return data
            else:
                logger.warning(f"Batch reference not found in Redis: {redis_key}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving batch reference from Redis: {e}")
            return None

    def store_fragment_reference(
        self,
        parent_doc_id: str,
        fragment_id: str,
        fragment_data: Dict[str, Any],
        ttl_override: Optional[int] = None,
    ) -> str:
        """Store document fragment reference in Redis."""
        try:
            redis_key = self.KEY_PATTERNS["fragment"].format(
                parent_doc_id=parent_doc_id, fragment_id=fragment_id
            )

            # Add metadata
            fragment_data["parent_doc_id"] = parent_doc_id
            fragment_data["fragment_id"] = fragment_id
            fragment_data["stored_at"] = datetime.utcnow().isoformat()

            # Serialize fragment data
            serialized_data = json.dumps(fragment_data, default=self._json_serializer)

            # Store in Redis with TTL
            ttl = ttl_override or self.TTL_SETTINGS["fragment"]
            self.redis.setex(redis_key, ttl, serialized_data)

            logger.info(
                f"Stored fragment reference in Redis: {redis_key} (TTL: {ttl}s)"
            )
            return redis_key

        except Exception as e:
            logger.error(f"Error storing fragment reference in Redis: {e}")
            raise

    def retrieve_fragment_reference(
        self, parent_doc_id: str, fragment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve document fragment reference from Redis."""
        try:
            redis_key = self.KEY_PATTERNS["fragment"].format(
                parent_doc_id=parent_doc_id, fragment_id=fragment_id
            )

            fragment_data = self.redis.get(redis_key)
            if fragment_data:
                data = json.loads(fragment_data)
                logger.debug(f"Retrieved fragment reference from Redis: {redis_key}")
                return data
            else:
                logger.warning(f"Fragment reference not found in Redis: {redis_key}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving fragment reference from Redis: {e}")
            return None

    def extend_ttl(
        self, redis_key: str, data_type: str, ttl_override: Optional[int] = None
    ) -> bool:
        """Extend the TTL for a Redis key."""
        try:
            ttl = ttl_override or self.TTL_SETTINGS.get(data_type, 86400)
            result = self.redis.expire(redis_key, ttl)

            if result:
                logger.info(f"Extended TTL for Redis key: {redis_key} (TTL: {ttl}s)")
                return True
            else:
                logger.warning(f"Failed to extend TTL for Redis key: {redis_key}")
                return False

        except Exception as e:
            logger.error(f"Error extending TTL for Redis key: {e}")
            return False

    def delete_reference(self, redis_key: str) -> bool:
        """Delete a reference from Redis."""
        try:
            result = self.redis.delete(redis_key)

            if result:
                logger.info(f"Deleted Redis reference: {redis_key}")
                return True
            else:
                logger.warning(f"Failed to delete Redis reference: {redis_key}")
                return False

        except Exception as e:
            logger.error(f"Error deleting Redis reference: {e}")
            return False

    def get_key_info(self, redis_key: str) -> Dict[str, Any]:
        """Get information about a Redis key."""
        try:
            info = {
                "key": redis_key,
                "exists": False,
                "ttl": -1,
                "type": None,
                "size": 0,
            }

            # Check if key exists
            if self.redis.exists(redis_key):
                info["exists"] = True

                # Get TTL
                ttl = self.redis.ttl(redis_key)
                info["ttl"] = ttl

                # Get key type
                key_type = self.redis.type(redis_key)
                info["type"] = key_type

                # Get value size
                if key_type == "string":
                    value = self.redis.get(redis_key)
                    if value:
                        info["size"] = len(value)

            return info

        except Exception as e:
            logger.error(f"Error getting key info: {e}")
            return {"key": redis_key, "error": str(e)}

    def cleanup_expired_keys(self, data_type: str, max_age_hours: int = 24) -> int:
        """Clean up expired keys for a specific data type."""
        try:
            # This is a simplified cleanup - in production, you'd use Redis SCAN
            # to iterate through keys and check TTL
            logger.info(f"Cleanup not implemented for data type: {data_type}")
            return 0

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get Redis memory usage statistics."""
        try:
            # Get Redis info
            info = self.redis.info("memory")

            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            }

        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {"error": str(e)}

    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "isoformat"):
            return obj.isoformat()
        else:
            return str(obj)

    def generate_reference_id(self, prefix: str = "ref") -> str:
        """Generate a unique reference ID."""
        return f"{prefix}_{uuid4().hex[:16]}"

    def validate_key_pattern(self, data_type: str, **kwargs) -> bool:
        """Validate that required parameters are present for a key pattern."""
        if data_type not in self.KEY_PATTERNS:
            return False

        pattern = self.KEY_PATTERNS[data_type]
        required_params = []

        # Extract required parameters from pattern
        if "{user_id}" in pattern:
            required_params.append("user_id")
        if "{doc_id}" in pattern:
            required_params.append("doc_id")
        if "{provider}" in pattern:
            required_params.append("provider")
        if "{message_id}" in pattern:
            required_params.append("message_id")
        if "{event_id}" in pattern:
            required_params.append("event_id")
        if "{contact_id}" in pattern:
            required_params.append("contact_id")
        if "{todo_id}" in pattern:
            required_params.append("todo_id")
        if "{batch_id}" in pattern:
            required_params.append("batch_id")
        if "{correlation_id}" in pattern:
            required_params.append("correlation_id")
        if "{fragment_id}" in pattern:
            required_params.append("fragment_id")
        if "{parent_doc_id}" in pattern:
            required_params.append("parent_doc_id")

        # Check if all required parameters are provided
        for param in required_params:
            if param not in kwargs:
                logger.warning(f"Missing required parameter for {data_type}: {param}")
                return False

        return True
