from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Column, DateTime, Field, SQLModel

from services.common import get_async_database_url
from services.office.core.settings import get_settings

# Global variables for lazy initialization
_engine = None
_async_session = None


def get_engine():
    """Get database engine with lazy initialization."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = get_async_database_url(settings.db_url_office)
        _engine = create_async_engine(database_url, echo=False)
    return _engine


def get_async_session_factory():
    """Get async session factory with lazy initialization."""
    global _async_session
    if _async_session is None:
        engine = get_engine()
        _async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


class Provider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class ApiCallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


# API Call Tracking
class ApiCall(SQLModel, table=True):
    __tablename__ = "api_calls"  # type: ignore[assignment]
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, max_length=255)
    provider: Provider = Field(sa_column=Column(SQLEnum(Provider), name="provider"))
    endpoint: str = Field(max_length=200)
    method: str = Field(max_length=10)
    status: ApiCallStatus = Field(
        sa_column=Column(SQLEnum(ApiCallStatus), name="status")
    )
    response_time_ms: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), index=True
        ),
    )


# Cache Entries
class CacheEntry(SQLModel, table=True):
    __tablename__ = "cache_entries"  # type: ignore[assignment]
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(unique=True, index=True, max_length=500)
    user_id: str = Field(index=True, max_length=255)
    provider: Provider = Field(sa_column=Column(SQLEnum(Provider), name="provider"))
    endpoint: str = Field(max_length=200)
    data: Dict[str, Any] = Field(sa_column=Column(JSON))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), index=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    last_accessed: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


# Rate Limiting
class RateLimitBucket(SQLModel, table=True):
    __tablename__ = "rate_limit_buckets"  # type: ignore[assignment]
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, max_length=255)
    provider: Provider = Field(sa_column=Column(SQLEnum(Provider), name="provider"))
    bucket_type: str = Field(max_length=50)  # "user_hourly", "provider_daily", etc.
    current_count: int = Field(default=0)
    window_start: datetime = Field(
        sa_column=Column(DateTime(timezone=True), index=True)
    )
    last_reset: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


# Database lifecycle management
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection."""
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        yield session


async def create_all_tables() -> None:
    """Create all database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    engine = get_engine()
    await engine.dispose()
