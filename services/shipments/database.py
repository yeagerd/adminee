# mypy: disable-error-code=no-untyped-def
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from services.common import get_async_database_url
from services.shipments.settings import get_settings

metadata = SQLModel.metadata

# Global engine and session factory - created once and reused
_engine = None


def get_engine():
    """Get or create the shared database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            get_async_database_url(settings.db_url_shipments),
            echo=settings.debug,
            future=True,
            # Add connection pool settings to prevent hangs
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )
    return _engine


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with proper resource management."""
    engine = get_engine()
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# FastAPI-compatible dependency
async def get_async_session_dep() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions."""
    async for session in get_async_session():
        yield session


# Database initialization is now handled by Alembic migrations
# Use 'alembic upgrade head' to initialize or update the database schema


async def create_all_tables_for_testing() -> None:
    """Create all database tables for testing only. Use Alembic migrations in production."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


def reset_db() -> None:
    """Reset database connections (useful for testing)."""
    global _engine
    _engine = None
