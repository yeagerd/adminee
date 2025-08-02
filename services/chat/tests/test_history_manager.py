# flake8: noqa: E402
pytest_plugins = ["pytest_asyncio"]

"""
Unit tests for history manager functionality.

Tests conversation history management, storage, retrieval,
and cleanup operations.
"""


import pytest
import pytest_asyncio  # Import pytest_asyncio

import services.chat.history_manager as hm


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Set up test settings and database for the entire test session."""
    import services.chat.settings as chat_settings

    # Create test settings instance
    test_settings = chat_settings.Settings(
        db_url_chat="sqlite+aiosqlite:///file::memory:?cache=shared",
        api_frontend_chat_key="test-frontend-chat-key",
        api_chat_user_key="test-chat-user-key",
        api_chat_office_key="test-chat-office-key",
        user_service_url="http://localhost:8001",
        office_service_url="http://localhost:8003",
    )

    # Save original singleton
    original_settings = chat_settings._settings

    # Set the test settings as the singleton
    chat_settings._settings = test_settings

    try:
        # Initialize database tables for testing
        from services.chat.history_manager import create_all_tables_for_testing

        await create_all_tables_for_testing()
        yield
    finally:
        # Restore original singleton
        chat_settings._settings = original_settings


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
    assert t.id is not None
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
async def test_update_message():
    """Test updating an existing message's content."""
    t = await hm.create_thread("user3", "Update Thread")
    assert t.id is not None

    # Create a message
    m = await hm.append_message(t.id, "user3", "Original content")
    assert m.content == "Original content"

    # Update the message
    updated_m = await hm.update_message(m.id, "Updated content")
    assert updated_m is not None
    assert updated_m.content == "Updated content"
    assert updated_m.id == m.id

    # Verify the update is persisted
    history = await hm.get_thread_history(t.id)
    updated_from_history = next(msg for msg in history if msg.id == m.id)
    assert updated_from_history.content == "Updated content"

    # Test updating non-existent message
    non_existent = await hm.update_message(99999, "Should not work")
    assert non_existent is None


@pytest.mark.asyncio
async def test_create_update_delete_draft():
    t = await hm.create_thread("user3", "Draft Thread")
    assert t.id is not None
    # Create a user draft
    d1 = await hm.create_user_draft(
        user_id="user3",
        draft_type="email",
        content="Draft 1",
        thread_id=t.id,
    )
    assert d1.content == "Draft 1"
    # Update the user draft
    d2 = await hm.update_user_draft(
        draft_id=d1.id,
        content="Draft 2",
    )
    assert d2.content == "Draft 2"
    d = await hm.get_user_draft(d1.id)
    assert d is not None
    assert d.content == "Draft 2"
    await hm.delete_user_draft(d1.id)
    d_none = await hm.get_user_draft(d1.id)
    assert d_none is None


@pytest.mark.asyncio
async def test_draft_unique_constraint():
    t = await hm.create_thread("user4", "Unique Draft Thread")
    assert t.id is not None
    # Clean up any existing drafts for this user/thread/type
    drafts = await hm.list_user_drafts("user4", draft_type="calendar_event")
    for d in drafts:
        await hm.delete_user_draft(d.id)
    # Create a user draft
    d1 = await hm.create_user_draft(
        user_id="user4",
        draft_type="calendar_event",
        content="Event 1",
        thread_id=t.id,
    )
    assert d1.content == "Event 1"
    # Create another draft of the same type (should create a new draft, not update)
    d2 = await hm.create_user_draft(
        user_id="user4",
        draft_type="calendar_event",
        content="Event 2",
        thread_id=t.id,
    )
    assert d2.content == "Event 2"
    # There should be only one draft for this user and thread/type
    drafts = await hm.list_user_drafts("user4", draft_type="calendar_event")
    assert len(drafts) == 1
    assert any(d.content == "Event 2" for d in drafts)


@pytest.mark.asyncio
async def test_pagination_and_ordering():
    t = await hm.create_thread("user5", "Paginate Thread")
    assert t.id is not None
    for i in range(10):
        await hm.append_message(t.id, "user5", f"msg {i}")
    msgs = await hm.get_thread_history(t.id, limit=5, offset=0)
    assert len(msgs) == 5
    assert msgs[0].created_at >= msgs[-1].created_at
