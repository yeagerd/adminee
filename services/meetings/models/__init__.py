from contextlib import asynccontextmanager, contextmanager
from threading import Lock
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
_engine: Engine | None = None
_async_engine: AsyncEngine | None = None
_session_maker: sessionmaker | None = None
_async_session_maker: async_sessionmaker | None = None

# Thread-safe initialization locks
_engine_lock = Lock()
_async_engine_lock = Lock()
_session_maker_lock = Lock()
_async_session_maker_lock = Lock()


def get_engine() -> "Engine":
    """Get or create the shared database engine in a thread-safe manner."""
    global _engine
    if _engine is None:
        with _engine_lock:
            # Double-check pattern to prevent race conditions
            if _engine is None:
                db_url = get_settings().db_url_meetings
                _engine = create_engine(
                    db_url,
                    echo=False,
                    future=True,
                    # Add connection pool settings to prevent connection exhaustion
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                )
    return _engine


def get_async_engine() -> "AsyncEngine":
    """Get or create the shared async database engine in a thread-safe manner."""
    global _async_engine
    if _async_engine is None:
        with _async_engine_lock:
            # Double-check pattern to prevent race conditions
            if _async_engine is None:
                db_url = get_settings().db_url_meetings
                async_db_url = get_async_database_url(db_url)
                # Configure asyncpg timeout parameters for better reliability
                connect_args = {}
                if async_db_url.startswith("postgresql"):
                    # command_timeout sets the default timeout for operations
                    connect_args["command_timeout"] = 10.0  # 10 seconds
                    # timeout sets the connection timeout
                    connect_args["timeout"] = 30.0  # 30 seconds
                
                _async_engine = create_async_engine(
                    async_db_url,
                    echo=False,
                    future=True,
                    # Add connection pool settings to prevent hangs
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                    # Apply database-specific connect_args
                    connect_args=connect_args,
                )
    return _async_engine


def get_sessionmaker() -> sessionmaker:
    """Get or create the shared session maker in a thread-safe manner.

    Acquire locks in sessionmaker -> engine order to avoid races with reset/close.
    Ensure the sessionmaker binds to a current (non-disposed) engine reference.
    """
    global _session_maker, _engine
    if _session_maker is None:
        with _session_maker_lock:
            if _session_maker is None:
                # Hold engine lock while reading/creating engine to avoid races
                with _engine_lock:
                    if _engine is None:
                        db_url = get_settings().db_url_meetings
                        _engine = create_engine(
                            db_url,
                            echo=False,
                            future=True,
                            pool_size=10,
                            max_overflow=20,
                            pool_timeout=30,
                            pool_recycle=3600,
                            pool_pre_ping=True,
                        )
                    current_engine = _engine
                _session_maker = sessionmaker(
                    bind=current_engine, autoflush=False, autocommit=False, future=True
                )
    return _session_maker


def get_async_sessionmaker() -> async_sessionmaker:
    """Get or create the shared async session maker in a thread-safe manner.

    Acquire locks in sessionmaker -> engine order to avoid races with reset/close.
    Ensure the sessionmaker binds to a current (non-disposed) async engine.
    """
    global _async_session_maker, _async_engine
    if _async_session_maker is None:
        with _async_session_maker_lock:
            if _async_session_maker is None:
                # Hold async engine lock while reading/creating engine to avoid races
                with _async_engine_lock:
                    if _async_engine is None:
                        db_url = get_settings().db_url_meetings
                        async_db_url = get_async_database_url(db_url)
                        # Configure asyncpg timeout parameters for better reliability
                        connect_args = {}
                        if async_db_url.startswith("postgresql"):
                            # command_timeout sets the default timeout for operations
                            connect_args["command_timeout"] = 10.0  # 10 seconds
                            # timeout sets the connection timeout
                            connect_args["timeout"] = 30.0  # 30 seconds
                        
                        _async_engine = create_async_engine(
                            async_db_url,
                            echo=False,
                            future=True,
                            pool_size=10,
                            max_overflow=20,
                            pool_timeout=30,
                            pool_recycle=3600,
                            pool_pre_ping=True,
                            # Apply database-specific connect_args
                            connect_args=connect_args,
                        )
                    current_async_engine = _async_engine
                _async_session_maker = async_sessionmaker(
                    bind=current_async_engine,
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
    """Close database connections in a thread-safe manner."""
    global _engine, _async_engine, _session_maker, _async_session_maker
    # Capture references under locks and clear globals first to avoid awaiting while holding locks
    async_engine_to_dispose: Optional[AsyncEngine] = None
    engine_to_dispose: Optional[Engine] = None

    # Async path: clear sessionmaker unconditionally, then clear engine if present (sessionmaker -> engine order)
    with _async_session_maker_lock:
        _async_session_maker = None
        with _async_engine_lock:
            if _async_engine is not None:
                async_engine_to_dispose = _async_engine
                _async_engine = None

    # Sync path: clear sessionmaker unconditionally, then clear engine if present (sessionmaker -> engine order)
    with _session_maker_lock:
        _session_maker = None
        with _engine_lock:
            if _engine is not None:
                engine_to_dispose = _engine
                _engine = None

    # Now dispose outside of locks
    if async_engine_to_dispose is not None:
        await async_engine_to_dispose.dispose()
    if engine_to_dispose is not None:
        engine_to_dispose.dispose()


def reset_db() -> None:
    """Reset database connections (useful for testing) in a thread-safe manner.

    Does not dispose engines; use close_db() when disposing is required.
    """
    global _engine, _async_engine, _session_maker, _async_session_maker
    # Reset async globals under locks (sessionmaker -> engine order)
    with _async_session_maker_lock:
        with _async_engine_lock:
            _async_session_maker = None
            _async_engine = None
    # Reset sync globals under locks (sessionmaker -> engine order)
    with _session_maker_lock:
        with _engine_lock:
            _session_maker = None
            _engine = None
