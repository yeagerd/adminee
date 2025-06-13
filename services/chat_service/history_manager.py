"""
History manager for chat_service: manages threads, messages, and drafts using SQLModel.

This module defines the database models and data access layer for the chat service.
It follows a clear architectural pattern where database models are separate from
API response models to ensure proper separation of concerns.

Database Models vs. API Response Models:
- Database models (Thread, Message, Draft) use SQLModel for ORM functionality
- API models (ThreadResponse, MessageResponse) use Pydantic for serialization
- This separation allows for type safety, field transformation, and independent evolution

Key Design Decisions:
- Database models use proper types (int IDs, datetime objects)
- API models use strings for JSON serialization compatibility
- API models can add computed fields not present in database
- API models control exactly what data is exposed to clients
"""

import datetime
from typing import List, Optional

from sqlalchemy import Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import registry
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, select

from services.chat_service.settings import get_settings


def get_database_url() -> str:
    """Get database URL with lazy initialization and proper error handling."""
    try:
        settings = get_settings()
        if not settings.db_url_chat:
            raise ValueError(
                "Database URL not configured. Please set DB_URL_CHAT environment variable."
            )
        return settings.db_url_chat
    except Exception as e:
        raise RuntimeError(
            f"Failed to get database configuration: {e}. "
            "Ensure DB_URL_CHAT environment variable is properly set."
        ) from e


def get_async_database_url(url: str) -> str:
    """Convert database URL to async format."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        return url


# Create a separate registry for chat service models to avoid conflicts with other services
chat_registry = registry()


# Create a custom SQLModel base that uses our isolated registry
class ChatSQLModel(SQLModel, registry=chat_registry):
    pass


# Global variables for lazy initialization
_engine = None
_async_session = None


def get_engine():
    """Get database engine with lazy initialization."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        async_url = get_async_database_url(database_url)
        _engine = create_async_engine(async_url, echo=False)
    return _engine


def get_async_session_factory():
    """Get async session factory with lazy initialization."""
    global _async_session
    if _async_session is None:
        engine = get_engine()
        _async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


class Thread(ChatSQLModel, table=True):
    """
    Database model for chat threads.

    Represents a conversation thread between a user and the AI assistant.
    This is the database/ORM representation with proper types and relationships.

    Note: This model is separate from ThreadResponse (API model) to maintain
    clean separation between data persistence and API contracts.

    Database Design:
    - Uses integer primary key for efficiency
    - Includes proper datetime objects with timezone support
    - Has SQLAlchemy relationships to related entities
    - Optimized for database operations and queries

    API Serialization:
    - Convert to ThreadResponse for API responses
    - ThreadResponse uses string types for JSON compatibility
    - ThreadResponse excludes internal relationships
    """

    __tablename__ = "threads"
    __table_args__ = {"extend_existing": True}

    # Primary key - integer for database efficiency
    id: Optional[int] = Field(default=None, primary_key=True)

    # User identifier - indexed for query performance
    user_id: str = Field(index=True, max_length=128)

    # Timestamps with timezone support and automatic updates
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

    # Optional thread title for organization
    title: Optional[str] = Field(default=None, max_length=256)

    # SQLAlchemy relationships - not exposed in API models
    messages: list["Message"] = Relationship(back_populates="thread")
    drafts: list["Draft"] = Relationship(back_populates="thread")


class Message(ChatSQLModel, table=True):
    """
    Database model for chat messages.

    Represents individual messages within a chat thread, from either user or assistant.
    This is the database/ORM representation optimized for storage and retrieval.

    Note: This model is separate from MessageResponse (API model) to maintain
    clean separation between data persistence and API contracts.

    Database Design:
    - Uses integer primary key and foreign key for efficiency
    - Stores content in TEXT column for large messages
    - Includes proper datetime objects with timezone support
    - Has SQLAlchemy relationship to parent thread

    API Serialization:
    - Convert to MessageResponse for API responses
    - MessageResponse adds computed fields like llm_generated
    - MessageResponse uses string IDs for JSON compatibility
    - MessageResponse excludes internal relationships
    """

    __tablename__ = "messages"
    __table_args__ = {"extend_existing": True}

    # Primary key - integer for database efficiency
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to parent thread
    thread_id: int = Field(foreign_key="threads.id")

    # User identifier - indexed for query performance
    user_id: str = Field(index=True, max_length=128)

    # Message content - using TEXT column for large messages
    content: str = Field(sa_column=Column(Text))

    # Timestamps with timezone support and automatic updates
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

    # SQLAlchemy relationship - not exposed in API models
    thread: Optional[Thread] = Relationship(back_populates="messages")


class Draft(ChatSQLModel, table=True):
    """
    Database model for draft content (emails, calendar events, etc.).

    Represents draft content that the AI assistant has prepared but not yet sent.
    Enforces one active draft per thread per type through unique constraint.

    Database Design:
    - Uses integer primary key for efficiency
    - Enforces unique constraint on (thread_id, type)
    - Stores draft content in TEXT column
    - Includes proper datetime objects with timezone support
    """

    __tablename__ = "drafts"
    __table_args__ = (
        UniqueConstraint("thread_id", "type", name="uq_thread_type"),
        {"extend_existing": True},
    )

    # Primary key - integer for database efficiency
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to parent thread
    thread_id: int = Field(foreign_key="threads.id")

    # Draft type (e.g., 'email', 'calendar_event', 'calendar_change')
    type: str = Field(index=True, max_length=64)

    # Draft content - using TEXT column for large content
    content: str = Field(sa_column=Column(Text))

    # Timestamps with timezone support and automatic updates
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

    # SQLAlchemy relationship - not exposed in API models
    thread: Optional[Thread] = Relationship(back_populates="drafts")


# Ensure tables are created on import
async def init_db():
    async with get_engine().begin() as conn:
        await conn.run_sync(chat_registry.metadata.create_all)


# Initialize database synchronously for backward compatibility
def init_db_sync():
    import asyncio

    try:
        asyncio.get_running_loop()
        # If we're in an async context, schedule the coroutine
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, init_db())
            future.result()
    except RuntimeError:
        # No running loop, we can run directly
        asyncio.run(init_db())


# Don't automatically initialize on import - let the application control this
# init_db_sync()


# Utility functions for thread, message, and draft management
async def get_session():
    """Get async database session."""
    async with get_async_session_factory()() as session:
        yield session


async def create_thread(user_id: str, title: Optional[str] = None) -> Thread:
    async with get_async_session_factory()() as session:
        thread = Thread(user_id=user_id, title=title)
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        return thread


async def list_threads(user_id: str) -> List[Thread]:
    async with get_async_session_factory()() as session:
        result = await session.execute(select(Thread).where(Thread.user_id == user_id))
        return list(result.scalars().all())


async def append_message(thread_id: int, user_id: str, content: str) -> Message:
    async with get_async_session_factory()() as session:
        message = Message(thread_id=thread_id, user_id=user_id, content=content)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


async def get_thread_history(
    thread_id: int, limit: int = 50, offset: int = 0
) -> List[Message]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.__table__.c.created_at.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


async def create_or_update_draft(
    thread_id: int, draft_type: str, content: str
) -> Draft:
    async with get_async_session_factory()() as session:
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
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id, Draft.type == draft_type)
        )
        draft = result.scalar_one_or_none()
        if draft:
            await session.delete(draft)
            await session.commit()


async def get_draft(thread_id: int, draft_type: str) -> Optional[Draft]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id, Draft.type == draft_type)
        )
        return result.scalar_one_or_none()


async def list_drafts(thread_id: int) -> List[Draft]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Draft).where(Draft.thread_id == thread_id)
        )
        return list(result.scalars().all())


async def get_thread(thread_id: int) -> Optional[Thread]:
    async with get_async_session_factory()() as session:
        result = await session.execute(select(Thread).where(Thread.id == thread_id))
        return result.scalar_one_or_none()
