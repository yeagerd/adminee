from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from services.shipments.settings import get_settings
from contextlib import asynccontextmanager

settings = get_settings()
DATABASE_URL = settings.db_url_shipments

engine = create_async_engine(
    DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    echo=settings.debug,
    future=True,
)

metadata = SQLModel.metadata

@asynccontextmanager
async def get_async_session():
    async with AsyncSession(engine) as session:
        yield session

# FastAPI-compatible dependency
async def get_async_session_dep():
    async with AsyncSession(engine) as session:
        yield session

def create_all_tables():
    import asyncio
    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    asyncio.run(_create())

def close_db():
    pass  # For symmetry with other services
