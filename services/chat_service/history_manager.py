"""
History manager for chat_service: manages threads, messages, and drafts using Ormar ORM.
"""

import datetime
import os
from typing import List, Optional

import databases
import ormar
import sqlalchemy

# Read DATABASE_URL from environment, default to in-memory if not set
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///memory")
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()


class Thread(ormar.Model):
    class Meta:
        tablename = "threads"

    ormar_config = ormar.OrmarConfig(
        metadata=metadata,
        database=database,
        tablename="threads",
    )
    id: int = ormar.Integer(primary_key=True)
    user_id: str = ormar.String(max_length=128, index=True)
    created_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)
    updated_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)
    title: Optional[str] = ormar.String(max_length=256, nullable=True)


class Message(ormar.Model):
    class Meta:
        tablename = "messages"

    ormar_config = ormar.OrmarConfig(
        metadata=metadata,
        database=database,
        tablename="messages",
    )
    id: int = ormar.Integer(primary_key=True)
    thread: Thread = ormar.ForeignKey(Thread, related_name="messages")
    user_id: str = ormar.String(max_length=128, index=True)
    content: str = ormar.Text()
    created_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)
    updated_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)


class Draft(ormar.Model):
    class Meta:
        tablename = "drafts"
        constraints = [ormar.UniqueColumns("thread", "type")]

    ormar_config = ormar.OrmarConfig(
        metadata=metadata,
        database=database,
        tablename="drafts",
        constraints=[ormar.UniqueColumns("thread", "type")],
    )
    id: int = ormar.Integer(primary_key=True)
    thread: Thread = ormar.ForeignKey(Thread, related_name="drafts")
    type: str = ormar.String(
        max_length=64, index=True
    )  # e.g., 'email', 'calendar_event', 'calendar_change'
    content: str = ormar.Text()
    created_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)
    updated_at: datetime.datetime = ormar.DateTime(default=datetime.datetime.utcnow)


# Ensure tables are created on import
def init_db():
    engine = sqlalchemy.create_engine(DATABASE_URL)
    metadata.create_all(engine)


init_db()


# Utility functions for thread, message, and draft management
async def create_thread(user_id: str, title: Optional[str] = None) -> Thread:
    return await Thread.objects.create(user_id=user_id, title=title)


async def list_threads(user_id: str) -> List[Thread]:
    return await Thread.objects.filter(user_id=user_id).all()


async def append_message(thread_id: int, user_id: str, content: str) -> Message:
    thread = await Thread.objects.get(id=thread_id)
    return await Message.objects.create(thread=thread, user_id=user_id, content=content)


async def get_thread_history(
    thread_id: int, limit: int = 50, offset: int = 0
) -> List[Message]:
    return (
        await Message.objects.filter(thread=thread_id)
        .order_by("-created_at")
        .offset(offset)
        .limit(limit)
        .all()
    )


async def create_or_update_draft(
    thread_id: int, draft_type: str, content: str
) -> Draft:
    draft = await Draft.objects.filter(thread=thread_id, type=draft_type).get_or_none()
    if draft:
        draft.content = content
        draft.updated_at = datetime.datetime.now(datetime.UTC)
        await draft.update()
        return draft
    thread = await Thread.objects.get(id=thread_id)
    return await Draft.objects.create(thread=thread, type=draft_type, content=content)


async def delete_draft(thread_id: int, draft_type: str) -> None:
    draft = await Draft.objects.filter(thread=thread_id, type=draft_type).get_or_none()
    if draft:
        await draft.delete()


async def get_draft(thread_id: int, draft_type: str) -> Optional[Draft]:
    return await Draft.objects.filter(thread=thread_id, type=draft_type).get_or_none()


async def list_drafts(thread_id: int) -> List[Draft]:
    return await Draft.objects.filter(thread=thread_id).all()


async def get_thread(thread_id: int) -> Optional[Thread]:
    return await Thread.objects.get_or_none(id=thread_id)
