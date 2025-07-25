# mypy: disable-error-code=no-untyped-def
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from services.common import get_async_database_url
from services.shipments.settings import get_settings

settings = get_settings()
DATABASE_URL = settings.db_url_shipments
engine = create_async_engine(
    get_async_database_url(DATABASE_URL),
    echo=settings.debug,
    future=True,
)

metadata = SQLModel.metadata


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session


# FastAPI-compatible dependency
async def get_async_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session


def create_all_tables() -> None:  # type: ignore[no-untyped-def]
    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(_create())


def close_db() -> None:
    pass  # For symmetry with other services
