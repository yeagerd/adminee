from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import databases
import ormar
import sqlalchemy
from core.config import settings

# Database setup
database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()


# Base OrmarConfig for all models
base_ormar_config = ormar.OrmarConfig(database=database, metadata=metadata)


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
    ormar_config = base_ormar_config.copy(tablename="api_calls")

    id: int = ormar.Integer(primary_key=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.Enum(enum_class=Provider)
    endpoint: str = ormar.String(max_length=200)
    method: str = ormar.String(max_length=10)
    status: ApiCallStatus = ormar.Enum(enum_class=ApiCallStatus)
    response_time_ms: Optional[int] = ormar.Integer(nullable=True)
    error_message: Optional[str] = ormar.Text(nullable=True)
    created_at: datetime = ormar.DateTime(
        default=lambda: datetime.now(timezone.utc), index=True
    )


# Cache Entries
class CacheEntry(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="cache_entries")

    id: int = ormar.Integer(primary_key=True)
    cache_key: str = ormar.String(max_length=500, unique=True, index=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.Enum(enum_class=Provider)
    endpoint: str = ormar.String(max_length=200)
    data: Dict[str, Any] = ormar.JSON()
    expires_at: datetime = ormar.DateTime(index=True)
    created_at: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))


# Rate Limiting
class RateLimitBucket(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="rate_limit_buckets")

    id: int = ormar.Integer(primary_key=True)
    user_id: str = ormar.String(max_length=255, index=True)
    provider: Provider = ormar.Enum(enum_class=Provider)
    bucket_type: str = ormar.String(
        max_length=50
    )  # "user_hourly", "provider_daily", etc.
    current_count: int = ormar.Integer(default=0)
    window_start: datetime = ormar.DateTime(index=True)
    last_reset: datetime = ormar.DateTime(default=lambda: datetime.now(timezone.utc))
