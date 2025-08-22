# mypy: disable-error-code=no-untyped-def
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from services.common import get_async_database_url
from services.shipments.settings import get_settings

metadata = SQLModel.metadata


def get_engine():
    """Get database engine with lazy settings loading."""
    settings = get_settings()
    database_url = get_async_database_url(settings.db_url_shipments)
    
    # Configure asyncpg timeout parameters for better reliability
    connect_args = {}
    if database_url.startswith("postgresql"):
        # command_timeout sets the default timeout for operations
        connect_args["command_timeout"] = 10.0  # 10 seconds
        # timeout sets the connection timeout
        connect_args["timeout"] = 30.0  # 30 seconds
    
    return create_async_engine(
        database_url,
        echo=settings.debug,
        future=True,
        # Add connection pool settings to prevent hangs
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        # Apply database-specific connect_args
        connect_args=connect_args,
    )


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine()
    async with AsyncSession(engine) as session:
        yield session


# FastAPI-compatible dependency
async def get_async_session_dep() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine()
    async with AsyncSession(engine) as session:
        yield session


# Database initialization is now handled by Alembic migrations
# Use 'alembic upgrade head' to initialize or update the database schema


async def create_all_tables_for_testing() -> None:
    """Create all database tables for testing only. Use Alembic migrations in production."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def close_db() -> None:
    pass  # For symmetry with other services
