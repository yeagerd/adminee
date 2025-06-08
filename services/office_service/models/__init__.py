from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import databases
import ormar
import sqlalchemy

from services.office_service.core.config import settings

# Database setup
database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()


class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database


class Provider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class ApiCallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


# API Call Tracking
class ApiCall(ormar.Model):
    class Meta(BaseMeta):
        tablename = "api_calls"

    id: int = ormar.Integer(primary_key=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.String(max_length=20, choices=list(Provider))
    endpoint: str = ormar.String(max_length=200)
    method: str = ormar.String(max_length=10)
    status: ApiCallStatus = ormar.String(max_length=20, choices=list(ApiCallStatus))
    response_time_ms: Optional[int] = ormar.Integer(nullable=True)
    error_message: Optional[str] = ormar.Text(nullable=True)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow, index=True)


# Cache Entries
class CacheEntry(ormar.Model):
    class Meta(BaseMeta):
        tablename = "cache_entries"

    id: int = ormar.Integer(primary_key=True)
    cache_key: str = ormar.String(max_length=500, unique=True, index=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.String(max_length=20, choices=list(Provider))
    endpoint: str = ormar.String(max_length=200)
    data: Dict[str, Any] = ormar.JSON()
    expires_at: datetime = ormar.DateTime(index=True)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
    last_accessed: datetime = ormar.DateTime(default=datetime.utcnow)


# Rate Limiting
class RateLimitBucket(ormar.Model):
    class Meta(BaseMeta):
        tablename = "rate_limit_buckets"

    id: int = ormar.Integer(primary_key=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.String(max_length=20, choices=list(Provider))
    bucket_type: str = ormar.String(
        max_length=50
    )  # "user_hourly", "provider_daily", etc.
    current_count: int = ormar.Integer(default=0)
    window_start: datetime = ormar.DateTime(index=True)
    last_reset: datetime = ormar.DateTime(default=datetime.utcnow)
