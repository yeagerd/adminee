from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlmodel import SQLModel

from services.common import get_async_database_url

# Import all models so they are registered with metadata
from services.contacts.models.contact import Contact  # noqa: F401
from services.contacts.settings import get_settings

# Base class for models
Base = declarative_base()

# Export metadata for Alembic (use SQLModel.metadata since Contact inherits from SQLModel)
metadata = SQLModel.metadata

# Global variables for lazy initialization
_engine: AsyncEngine | None = None
_async_session_local: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get database engine with lazy initialization."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = settings.db_url_contacts
        _engine = create_async_engine(get_async_database_url(database_url), echo=False)
    return _engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get async session factory with lazy initialization."""
    global _async_session_local
    if _async_session_local is None:
        engine = get_engine()
        _async_session_local = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_local


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        yield session


async def create_tables() -> None:
    """Create all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Drop all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
