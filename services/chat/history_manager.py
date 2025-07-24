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
from typing import Any, AsyncGenerator, List, Optional

from sqlalchemy import Text, UniqueConstraint, desc, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import registry
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, select

from services.chat.settings import get_settings


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


def get_engine() -> Any:
    """Get database engine with lazy initialization."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        async_url = get_async_database_url(database_url)
        _engine = create_async_engine(async_url, echo=False)
    return _engine


def get_async_session_factory() -> Any:
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

    __tablename__ = "threads"  # type: ignore[assignment]
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
    user_drafts: list["UserDraft"] = Relationship(back_populates="thread")


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

    __tablename__ = "messages"  # type: ignore[assignment]
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

    __tablename__ = "drafts"  # type: ignore[assignment]
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


class UserDraft(ChatSQLModel, table=True):
    """
    Database model for user-created draft content.

    Represents draft content created by users (not AI-generated).
    Supports multiple drafts per user with different types.
    """

    __tablename__ = "user_drafts"  # type: ignore[assignment]
    __table_args__ = {"extend_existing": True}

    # Primary key - integer for database efficiency
    id: Optional[int] = Field(default=None, primary_key=True)

    # User identifier - indexed for query performance
    user_id: str = Field(index=True, max_length=128)

    # Draft type (e.g., 'email', 'calendar', 'document')
    type: str = Field(index=True, max_length=64)

    # Draft content - using TEXT column for large content
    content: str = Field(sa_column=Column(Text))

    # Draft metadata as JSON string
    draft_metadata: str = Field(sa_column=Column(Text), default="{}")

    # Draft status
    status: str = Field(default="draft", max_length=32)

    # Optional thread ID for AI-generated drafts that become user drafts
    thread_id: Optional[int] = Field(foreign_key="threads.id", default=None)

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
    thread: Optional[Thread] = Relationship(back_populates="user_drafts")


# Ensure tables are created on import
async def init_db() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(chat_registry.metadata.create_all)


# Initialize database synchronously for backward compatibility
def init_db_sync() -> None:
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
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with get_async_session_factory()() as session:
        yield session


async def create_thread(user_id: str, title: Optional[str] = None) -> Thread:
    async with get_async_session_factory()() as session:
        thread = Thread(user_id=user_id, title=title)
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

        # Ensure the ID was properly assigned by the database
        if thread.id is None:
            raise RuntimeError(
                f"Failed to create thread for user {user_id}: "
                "Database did not assign an ID after commit"
            )

        return thread


async def list_threads(user_id: str, limit: int = 20, offset: int = 0) -> List[Thread]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Thread)
            .where(Thread.user_id == user_id)
            .order_by(desc(Thread.updated_at))  # type: ignore[attr-defined, arg-type]
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


async def append_message(thread_id: int, user_id: str, content: str) -> Message:
    async with get_async_session_factory()() as session:
        message = Message(thread_id=thread_id, user_id=user_id, content=content)
        session.add(message)
        await session.commit()
        await session.refresh(message)

        # Ensure the ID was properly assigned by the database
        if message.id is None:
            raise RuntimeError(
                f"Failed to create message for thread {thread_id}: "
                "Database did not assign an ID after commit"
            )

        return message


async def update_message(message_id: int, content: str) -> Optional[Message]:
    """Update an existing message's content."""
    async with get_async_session_factory()() as session:
        result = await session.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()

        if message:
            message.content = content
            message.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await session.commit()
            await session.refresh(message)
            return message

        return None


async def get_thread_history(
    thread_id: int, limit: int = 50, offset: int = 0
) -> List[Message]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


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


# User Draft Management Functions
async def create_user_draft(
    user_id: str,
    draft_type: str,
    content: str,
    metadata: str = "{}",
    thread_id: Optional[int] = None,
) -> UserDraft:
    async with get_async_session_factory()() as session:
        draft = UserDraft(
            user_id=user_id,
            type=draft_type,
            content=content,
            draft_metadata=metadata,
            thread_id=thread_id,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        # Ensure the ID was properly assigned by the database
        if draft.id is None:
            raise RuntimeError(
                f"Failed to create user draft for user {user_id}: "
                "Database did not assign an ID after commit"
            )

        return draft


async def update_user_draft(
    draft_id: int,
    content: Optional[str] = None,
    metadata: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[UserDraft]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(UserDraft).where(UserDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()

        if not draft:
            return None

        if content is not None:
            draft.content = content
        if metadata is not None:
            draft.draft_metadata = metadata
        if status is not None:
            draft.status = status

        draft.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await session.commit()
        await session.refresh(draft)

        return draft


async def delete_user_draft(draft_id: int) -> bool:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(UserDraft).where(UserDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()

        if not draft:
            return False

        await session.delete(draft)
        await session.commit()
        return True


async def get_user_draft(draft_id: int) -> Optional[UserDraft]:
    async with get_async_session_factory()() as session:
        result = await session.execute(
            select(UserDraft).where(UserDraft.id == draft_id)
        )
        return result.scalar_one_or_none()


async def list_user_drafts(
    user_id: str,
    draft_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[UserDraft]:
    async with get_async_session_factory()() as session:
        query = select(UserDraft).where(UserDraft.user_id == user_id)

        if draft_type:
            query = query.where(UserDraft.type == draft_type)
        if status:
            query = query.where(UserDraft.status == status)

        query = query.order_by(UserDraft.updated_at.desc())  # type: ignore[attr-defined]
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())


async def count_user_drafts(
    user_id: str,
    draft_type: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    async with get_async_session_factory()() as session:
        query = (
            select(func.count())
            .select_from(UserDraft)
            .where(UserDraft.user_id == user_id)
        )
        if draft_type:
            query = query.where(UserDraft.type == draft_type)
        if status:
            query = query.where(UserDraft.status == status)
        result = await session.execute(query)
        return result.scalar_one()


async def get_thread(thread_id: int) -> Optional[Thread]:
    async with get_async_session_factory()() as session:
        result = await session.execute(select(Thread).where(Thread.id == thread_id))
        return result.scalar_one_or_none()
