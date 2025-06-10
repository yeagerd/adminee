"""
Database configuration for User Management Service.

Sets up database connection using SQLModel and SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .settings import settings


# Create async engine for database operations
def get_async_database_url(url: str) -> str:
    """Convert database URL to async format."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        return url


engine = create_async_engine(
    get_async_database_url(settings.database_url),
    echo=settings.debug,
)

# Session factory for dependency injection
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Database lifecycle management
async def get_session() -> AsyncSession:
    """Get async database session for dependency injection."""
    async with async_session() as session:
        yield session


async def create_all_tables():
    """Create all database tables. Use Alembic migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
