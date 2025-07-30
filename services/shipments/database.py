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
    return create_async_engine(
        get_async_database_url(settings.db_url_shipments),
        echo=settings.debug,
        future=True,
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


def create_all_tables() -> None:  # type: ignore[no-untyped-def]
    import asyncio

    async def _create():
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(_create())


def close_db() -> None:
    pass  # For symmetry with other services
