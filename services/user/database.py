"""
Database configuration for User Management Service.

Sets up database connection using SQLModel and SQLAlchemy.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlmodel import SQLModel

from services.common import get_async_database_url
from services.common.database_config import create_strict_async_engine
from services.user.models.audit import AuditLog  # noqa: F401
from services.user.models.integration import Integration  # noqa: F401
from services.user.models.preferences import UserPreferences  # noqa: F401
from services.user.models.token import EncryptedToken  # noqa: F401

# Import all models so SQLModel can find them for table creation
from services.user.models.user import User  # noqa: F401
from services.user.settings import get_settings


def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_strict_async_engine(
        get_async_database_url(settings.db_url_user),
        echo=settings.debug,
    )


def get_async_session() -> async_sessionmaker[AsyncSession]:
    engine = get_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Database lifecycle management
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection."""
    async_session = get_async_session()
    async with async_session() as session:
        yield session


# Database initialization is now handled by Alembic migrations
# Use 'alembic upgrade head' to initialize or update the database schema


# Export metadata for Alembic
metadata = SQLModel.metadata


async def create_all_tables_for_testing() -> None:
    """Create all database tables for testing only. Use Alembic migrations in production."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    engine = get_engine()
    await engine.dispose()
