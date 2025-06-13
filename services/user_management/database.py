"""
Database configuration for User Management Service.

Sets up database connection using SQLModel and SQLAlchemy.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from services.user_management.models.audit import AuditLog  # noqa: F401
from services.user_management.models.integration import Integration  # noqa: F401
from services.user_management.models.preferences import UserPreferences  # noqa: F401
from services.user_management.models.token import EncryptedToken  # noqa: F401

# Import all models so SQLModel can find them for table creation
from services.user_management.models.user import User  # noqa: F401
from services.user_management.settings import get_settings


# Create async engine for database operations
def get_async_database_url(url: str) -> str:
    """Convert database URL to async format."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        return url


def get_engine():
    settings = get_settings()
    return create_async_engine(
        get_async_database_url(settings.db_url_user_management),
        echo=settings.debug,
    )


def get_async_session():
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


async def create_all_tables():
    """Create all database tables. Use Alembic migrations in production."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Export metadata for Alembic
metadata = SQLModel.metadata


async def close_db():
    """Close database connections."""
    engine = get_engine()
    await engine.dispose()
