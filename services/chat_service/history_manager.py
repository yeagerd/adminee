"""
History manager for chat_service: manages threads, messages, and drafts using SQLModel.
"""

import datetime
import os
from typing import List, Optional

from sqlalchemy import Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, select

# Read DATABASE_URL from environment, default to file-based SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./chat_service.db")


def get_async_database_url(url: str) -> str:
    """Convert database URL to async format."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        return url


# Create async engine for database operations
engine = create_async_engine(get_async_database_url(DATABASE_URL), echo=False)

# Session factory for dependency injection
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Thread(SQLModel, table=True):
    __tablename__ = "threads"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, max_length=128)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        ),
    )
    title: Optional[str] = Field(default=None, max_length=256)

    # Relationships
    messages: list["Message"] = Relationship(back_populates="thread")
    drafts: list["Draft"] = Relationship(back_populates="thread")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="threads.id")
    user_id: str = Field(index=True, max_length=128)
    content: str = Field(sa_column=Column(Text))
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        ),
    )

    # Relationship
    thread: Optional[Thread] = Relationship(back_populates="messages")


class Draft(SQLModel, table=True):
    __tablename__ = "drafts"
    __table_args__ = (UniqueConstraint("thread_id", "type", name="uq_thread_type"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="threads.id")
    type: str = Field(
        index=True, max_length=64
    )  # e.g., 'email', 'calendar_event', 'calendar_change'
    content: str = Field(sa_column=Column(Text))
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        ),
    )

    # Relationship
    thread: Optional[Thread] = Relationship(back_populates="drafts")


# Ensure tables are created on import
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Initialize database synchronously for backward compatibility
def init_db_sync():
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # If we're in an async context, schedule the coroutine
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, init_db())
            future.result()
    else:
        loop.run_until_complete(init_db())


init_db_sync()


# Utility functions for thread, message, and draft management
async def get_session():
    """Get async database session."""
    async with async_session() as session:
        yield session


async def create_thread(user_id: str, title: Optional[str] = None) -> Thread:
    async with async_session() as session:
        thread = Thread(user_id=user_id, title=title)
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        return thread


async def list_threads(user_id: str) -> List[Thread]:
    async with async_session() as session:
        result = await session.execute(select(Thread).where(Thread.user_id == user_id))
        return result.scalars().all()


async def append_message(thread_id: int, user_id: str, content: str) -> Message:
    async with async_session() as session:
        message = Message(thread_id=thread_id, user_id=user_id, content=content)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


async def get_thread_history(
    thread_id: int, limit: int = 50, offset: int = 0
) -> List[Message]:
    async with async_session() as session:
        result = await session.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()


async def create_or_update_draft(
    thread_id: int, draft_type: str, content: str
) -> Draft:
    async with async_session() as session:
        # Try to get existing draft
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id, Draft.type == draft_type)
        )
        draft = result.scalar_one_or_none()

        if draft:
            draft.content = content
            draft.updated_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            draft = Draft(thread_id=thread_id, type=draft_type, content=content)
            session.add(draft)

        await session.commit()
        await session.refresh(draft)
        return draft


async def delete_draft(thread_id: int, draft_type: str) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id, Draft.type == draft_type)
        )
        draft = result.scalar_one_or_none()
        if draft:
            await session.delete(draft)
            await session.commit()


async def get_draft(thread_id: int, draft_type: str) -> Optional[Draft]:
    async with async_session() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id, Draft.type == draft_type)
        )
        return result.scalar_one_or_none()


async def list_drafts(thread_id: int) -> List[Draft]:
    async with async_session() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id)
        )
        return result.scalars().all()


async def get_thread(thread_id: int) -> Optional[Thread]:
    async with async_session() as session:
        result = await session.execute(select(Thread).where(Thread.id == thread_id))
        return result.scalar_one_or_none()
