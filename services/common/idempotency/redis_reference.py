import datetime

import redis


class RedisReferencePattern:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def store_idempotency_key(self, key: str, metadata: dict):
        metadata["stored_at"] = datetime.datetime.now(datetime.UTC).isoformat()

    def store_batch_reference(self, batch_data: dict):
        batch_data["stored_at"] = datetime.datetime.now(datetime.UTC).isoformat()
