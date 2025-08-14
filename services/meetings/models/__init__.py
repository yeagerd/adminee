from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

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
from meetings.models.booking_entities import AnalyticsEvent as AnalyticsEvent
from meetings.models.booking_entities import Booking as Booking
from meetings.models.booking_entities import BookingLink as BookingLink
from meetings.models.booking_entities import BookingTemplate as BookingTemplate
from meetings.models.booking_entities import OneTimeLink as OneTimeLink
from services.meetings.models.meeting import MeetingPoll as MeetingPoll
from services.meetings.models.meeting import PollParticipant as PollParticipant
from services.meetings.models.meeting import PollResponse as PollResponse
from services.meetings.models.meeting import TimeSlot as TimeSlot
from services.meetings.settings import get_settings


def get_engine() -> "Engine":
    db_url = get_settings().db_url_meetings
    return create_engine(db_url, echo=False, future=True)


def get_async_engine() -> "AsyncEngine":
    """Get async database engine for async operations."""
    db_url = get_settings().db_url_meetings
    async_db_url = get_async_database_url(db_url)
    return create_async_engine(async_db_url, echo=False, future=True)


def get_sessionmaker() -> sessionmaker:
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_async_sessionmaker() -> async_sessionmaker:
    """Get async session maker for async operations."""
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        class_=AsyncSession,
        expire_on_commit=False,
    )


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
