"""
End-to-end tests for chat service with multi-agent workflow.

Tests the complete chat service functionality including
multi-agent workflow processing, history management, and API endpoints.
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from services.chat import history_manager

# Test API key for authentication
TEST_API_KEY = "test-frontend-chat-key"
TEST_HEADERS = {"X-API-Key": TEST_API_KEY}


# Patch the environment before any imports that might use it
os.environ.update(
    {
        "DB_URL_CHAT": "sqlite+aiosqlite:///file::memory:?cache=shared",
        "OPENAI_API_KEY": "test-key-for-multi-agent",
        "LLM_MODEL": "gpt-4.1-nano",
        "LLM_PROVIDER": "openai",
        "API_FRONTEND_CHAT_KEY": TEST_API_KEY,
    }
)

from services.chat.auth import get_chat_auth  # noqa: E402

# Now import the app after setting up the environment


@pytest.fixture
def app():
    """Fixture to provide the FastAPI app with test environment."""
    # Force reload the auth module to pick up the new environment variables
    for module in list(sys.modules):
        if module.startswith("services.chat"):
            del sys.modules[module]

    # Re-import the app and auth to get fresh instances
    from services.chat.auth import _chat_auth as fresh_auth
    from services.chat.main import app as fresh_app

    # Update the global _chat_auth reference
    global _chat_auth
    _chat_auth = fresh_auth

    return fresh_app


async def setup_test_database():
    """Initialize the test database with tables."""
    await history_manager.init_db()


@pytest.fixture(autouse=True)
def setup_test_environment(app):
    """Set up the test environment."""
    # Initialize test database synchronously
    asyncio.run(setup_test_database())

    # Verify auth is properly set up
    auth = get_chat_auth()
    assert auth.verify_api_key_value(TEST_API_KEY) == "frontend"


# Test API key for authentication
TEST_API_KEY = "test-frontend-chat-key"
TEST_HEADERS = {"X-API-Key": TEST_API_KEY}


def test_end_to_end_chat_flow(app):
    client = TestClient(app)
    user_id = "testuser"

    # List threads (record initial count)
    resp = client.get("/threads", params={"user_id": user_id}, headers=TEST_HEADERS)
    assert resp.status_code == 200

    # Start a chat (should create a new thread and return response)
    msg = "Hello, world!"
    resp = client.post(
        "/chat", json={"user_id": user_id, "message": msg}, headers=TEST_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "thread_id" in data
    assert "messages" in data
    assert len(data["messages"]) > 0
    # Verify we got a response (content varies based on LLM availability)
    assert data["messages"][-1]["content"] is not None
    assert len(data["messages"][-1]["content"]) > 0

    thread_id = data["thread_id"]

    # Send another message in the same thread
    msg2 = "How are you?"
    resp = client.post(
        "/chat",
        json={"user_id": user_id, "thread_id": thread_id, "message": msg2},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200
    data2 = resp.json()
    assert data2["thread_id"] == thread_id
    # Verify we got a response (content varies based on LLM availability)
    assert data2["messages"][-1]["content"] is not None
    assert len(data2["messages"][-1]["content"]) > 0

    # List threads (should contain the thread we just used)
    resp = client.get("/threads", params={"user_id": user_id}, headers=TEST_HEADERS)
    assert resp.status_code == 200
    threads = resp.json()
    assert any(t["thread_id"] == thread_id for t in threads)

    # Get thread history
    resp = client.get(f"/threads/{thread_id}/history", headers=TEST_HEADERS)
    assert resp.status_code == 200
    history = resp.json()
    assert history["thread_id"] == thread_id
    assert len(history["messages"]) >= 2

    # Feedback endpoint
    last_msg = history["messages"][-1]
    resp = client.post(
        "/feedback",
        json={
            "user_id": user_id,
            "thread_id": thread_id,
            "message_id": last_msg["message_id"],
            "feedback": "up",
        },
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_multiple_blank_thread_creates_distinct_threads(app):
    client = TestClient(app)
    user_id = "testuser_multi"

    # Send first message with blank thread_id
    resp1 = client.post(
        "/chat",
        json={"user_id": user_id, "message": "First message"},
        headers=TEST_HEADERS,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    thread_id1 = data1["thread_id"]

    # Send second message with blank thread_id
    resp2 = client.post(
        "/chat",
        json={"user_id": user_id, "message": "Second message"},
        headers=TEST_HEADERS,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    thread_id2 = data2["thread_id"]

    # The thread IDs should be different
    assert thread_id1 != thread_id2

    # List threads and verify both thread IDs are present
    resp = client.get("/threads", params={"user_id": user_id}, headers=TEST_HEADERS)
    assert resp.status_code == 200
    threads = resp.json()
    thread_ids = {t["thread_id"] for t in threads}
    assert thread_id1 in thread_ids
    assert thread_id2 in thread_ids
