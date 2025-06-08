# flake8: noqa: E402
pytest_plugins = ["pytest_asyncio"]

import os
import tempfile

import pytest
import pytest_asyncio

from services.chat_service import history_manager as hm


@pytest_asyncio.fixture(scope="module")
async def temp_db():
    # Create a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Set the DATABASE_URL to use the temporary file
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Reinitialize the database with the new URL
    hm.database = hm.databases.Database(hm.DATABASE_URL)

    # Create tables and connect
    engine = hm.sqlalchemy.create_engine(hm.DATABASE_URL)
    hm.metadata.create_all(engine)
    await hm.database.connect()

    yield db_path

    # Cleanup
    await hm.database.disconnect()
    hm.metadata.drop_all(engine)
    os.unlink(db_path)


@pytest_asyncio.fixture(autouse=True)
async def clear_db(temp_db):
    # Clear data between tests
    async with hm.database:
        await hm.Message.objects.delete(each=True)
        await hm.Draft.objects.delete(each=True)
        await hm.Thread.objects.delete(each=True)
    yield


@pytest.mark.asyncio
async def test_create_and_list_threads():
    t1 = await hm.create_thread("user1", "Thread 1")
    t2 = await hm.create_thread("user1", "Thread 2")
    threads = await hm.list_threads("user1")
    assert len(threads) >= 2
    titles = [t.title for t in threads]
    ids = [t.id for t in threads]
    assert "Thread 1" in titles
    assert "Thread 2" in titles
    assert t1.id in ids
    assert t2.id in ids
    # Optionally, check that the thread objects match
    t1_from_list = next(t for t in threads if t.id == t1.id)
    t2_from_list = next(t for t in threads if t.id == t2.id)
    assert t1_from_list.title == "Thread 1"
    assert t2_from_list.title == "Thread 2"


@pytest.mark.asyncio
async def test_append_and_get_history():
    t = await hm.create_thread("user2", "History Thread")
    m1 = await hm.append_message(t.id, "user2", "Hello")
    m2 = await hm.append_message(t.id, "user2", "World")
    history = await hm.get_thread_history(t.id)
    assert len(history) == 2
    # Assert m1 and m2 are in history and their fields match
    contents = [msg.content for msg in history]
    ids = [msg.id for msg in history]
    assert m1.content == "Hello"
    assert m2.content == "World"
    assert m1.id in ids
    assert m2.id in ids
    # Assert contents contains both messages
    assert "Hello" in contents
    assert "World" in contents
    # Optionally, check that the message objects match
    m1_from_history = next(msg for msg in history if msg.id == m1.id)
    m2_from_history = next(msg for msg in history if msg.id == m2.id)
    assert m1_from_history.content == "Hello"
    assert m2_from_history.content == "World"


@pytest.mark.asyncio
async def test_create_update_delete_draft():
    t = await hm.create_thread("user3", "Draft Thread")
    d1 = await hm.create_or_update_draft(t.id, "email", "Draft 1")
    assert d1.content == "Draft 1"
    d2 = await hm.create_or_update_draft(t.id, "email", "Draft 2")
    assert d2.content == "Draft 2"
    d = await hm.get_draft(t.id, "email")
    assert d.content == "Draft 2"
    await hm.delete_draft(t.id, "email")
    d_none = await hm.get_draft(t.id, "email")
    assert d_none is None


@pytest.mark.asyncio
async def test_draft_unique_constraint():
    t = await hm.create_thread("user4", "Unique Draft Thread")
    d1 = await hm.create_or_update_draft(t.id, "calendar_event", "Event 1")
    assert d1.content == "Event 1"
    d2 = await hm.create_or_update_draft(t.id, "calendar_event", "Event 2")
    assert d2.content == "Event 2"
    assert d1.id == d2.id  # Should update, not create new
    drafts = await hm.list_drafts(t.id)
    assert len([d for d in drafts if d.type == "calendar_event"]) == 1
    assert drafts[0].content == "Event 2"


@pytest.mark.asyncio
async def test_pagination_and_ordering():
    t = await hm.create_thread("user5", "Paginate Thread")
    for i in range(10):
        await hm.append_message(t.id, "user5", f"msg {i}")
    msgs = await hm.get_thread_history(t.id, limit=5, offset=0)
    assert len(msgs) == 5
    assert msgs[0].created_at >= msgs[-1].created_at
