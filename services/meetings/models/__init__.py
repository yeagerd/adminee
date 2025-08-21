from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from services.common import get_async_database_url
from services.meetings.models.base import Base as Base
from services.meetings.models.booking_entities import AnalyticsEvent as AnalyticsEvent
from services.meetings.models.booking_entities import Booking as Booking
from services.meetings.models.booking_entities import BookingLink as BookingLink
from services.meetings.models.booking_entities import BookingTemplate as BookingTemplate
from services.meetings.models.booking_entities import OneTimeLink as OneTimeLink
from services.meetings.models.meeting import MeetingPoll as MeetingPoll
from services.meetings.models.meeting import PollParticipant as PollParticipant
from services.meetings.models.meeting import PollResponse as PollResponse
from services.meetings.models.meeting import TimeSlot as TimeSlot
from services.meetings.settings import get_settings

# Global engines and session factories - created once and reused
_engine: Optional[Engine] = None
_async_engine: Optional[AsyncEngine] = None
_session_maker: Optional[sessionmaker] = None
_async_session_maker: Optional[async_sessionmaker] = None


def get_engine() -> "Engine":
    """Get or create the shared database engine."""
    global _engine
    if _engine is None:
        db_url = get_settings().db_url_meetings
        _engine = create_engine(db_url, echo=False, future=True)
    return _engine


def get_async_engine() -> "AsyncEngine":
    """Get or create the shared async database engine."""
    global _async_engine
    if _async_engine is None:
        db_url = get_settings().db_url_meetings
        async_db_url = get_async_database_url(db_url)
        _async_engine = create_async_engine(
            async_db_url,
            echo=False,
            future=True,
            # Add connection pool settings to prevent hangs
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )
    return _async_engine


def get_sessionmaker() -> sessionmaker:
    """Get or create the shared session maker."""
    global _session_maker
    if _session_maker is None:
        engine = get_engine()
        _session_maker = sessionmaker(
            bind=engine, autoflush=False, autocommit=False, future=True
        )
    return _session_maker


def get_async_sessionmaker() -> async_sessionmaker:
    """Get or create the shared async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


@contextmanager
def get_session() -> Generator["Session", None, None]:
    Session = get_sessionmaker()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for async operations."""
    async_session_factory = get_async_sessionmaker()
    async with async_session_factory() as session:
        yield session


async def create_all_tables_for_testing() -> None:
    """Create all database tables for testing only. Use Alembic migrations in production."""
    engine = get_engine()
    from services.meetings.models.base import Base

    Base.metadata.create_all(engine)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _async_engine, _session_maker, _async_session_maker
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_maker = None
    if _engine:
        _engine.dispose()
        _engine = None
        _session_maker = None


def reset_db() -> None:
    """Reset database connections (useful for testing)."""
    global _engine, _async_engine, _session_maker, _async_session_maker
    _engine = None
    _async_engine = None
    _session_maker = None
    _async_session_maker = None
