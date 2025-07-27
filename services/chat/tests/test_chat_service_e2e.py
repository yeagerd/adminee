"""
End-to-end tests for chat service with multi-agent workflow.

Tests the complete chat service functionality including
multi-agent workflow processing, history management, and API endpoints.
"""

import asyncio
import os
import sys
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

# Test API key for authentication
TEST_API_KEY = "test-frontend-chat-key"
TEST_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture(scope="module")
def test_env():
    """Set up test environment variables."""
    env_vars = {
        "DB_URL_CHAT": "sqlite+aiosqlite:///file::memory:?cache=shared",
        # Don't set OPENAI_API_KEY so it falls back to FakeLLM
        "LLM_MODEL": "fake-model",
        "LLM_PROVIDER": "fake",
        "API_FRONTEND_CHAT_KEY": TEST_API_KEY,
        "USER_MANAGEMENT_SERVICE_URL": "http://localhost:8001",
        "OFFICE_SERVICE_URL": "http://localhost:8003",
    }
    with patch.dict("os.environ", env_vars):
        yield env_vars


@pytest.fixture
def app(test_env):
    """Fixture to provide the FastAPI app with test environment."""
    # Force reload the auth module to pick up the new environment variables
    for module in list(sys.modules):
        if module.startswith("services.chat"):
            del sys.modules[module]

    # Import after module cleanup to ensure fresh imports
    from services.chat import history_manager
    from services.chat.main import app as fresh_app

    # Update the global _history_manager reference
    global _history_manager
    _history_manager = history_manager

    return fresh_app


async def setup_test_database():
    """Initialize the test database with tables."""
    import services.chat.settings as chat_settings
    from services.chat import history_manager

    # Create test settings instance
    test_settings = chat_settings.Settings(
        db_url_chat="sqlite+aiosqlite:///file::memory:?cache=shared",
        api_frontend_chat_key="test-frontend-chat-key",
        api_chat_user_key="test-chat-user-key",
        api_chat_office_key="test-chat-office-key",
        user_management_service_url="http://localhost:8001",
        office_service_url="http://localhost:8003",
    )

    # Save original singleton
    original_settings = chat_settings._settings

    # Set the test settings as the singleton
    chat_settings._settings = test_settings

    try:
        await history_manager.init_db()
    finally:
        # Restore original singleton
        chat_settings._settings = original_settings


@pytest.fixture(autouse=True)
def setup_test_environment(app):
    """Set up the test environment."""
    # Initialize test database synchronously
    asyncio.run(setup_test_database())
    # Removed get_chat_auth import and assertion as it does not exist


@pytest.fixture(autouse=True, scope="session")
def set_db_url_chat():
    original_db_url = os.environ.get("DB_URL_CHAT")
    os.environ["DB_URL_CHAT"] = "sqlite+aiosqlite:///file::memory:?cache=shared"
    yield
    if original_db_url:
        os.environ["DB_URL_CHAT"] = original_db_url
    elif "DB_URL_CHAT" in os.environ:
        del os.environ["DB_URL_CHAT"]


def test_end_to_end_chat_flow(app):
    client = TestClient(app)
    user_id = "testuser"
    headers_with_user = {**TEST_HEADERS, "X-User-Id": user_id}

    # List threads (record initial count)
    resp = client.get("/v1/chat/threads", headers=headers_with_user)
    assert resp.status_code == 200

    # Start a chat (should create a new thread and return response)
    msg = "Hello, world!"
    resp = client.post(
        "/v1/chat/completions", json={"message": msg}, headers=headers_with_user
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
        "/v1/chat/completions",
        json={"thread_id": thread_id, "message": msg2},
        headers=headers_with_user,
    )
    assert resp.status_code == 200
    data2 = resp.json()
    assert data2["thread_id"] == thread_id
    # Verify we got a response (content varies based on LLM availability)
    assert data2["messages"][-1]["content"] is not None
    assert len(data2["messages"][-1]["content"]) > 0

    # List threads (should contain the thread we just used)
    resp = client.get("/v1/chat/threads", headers=headers_with_user)
    assert resp.status_code == 200
    threads_resp = resp.json()
    threads = threads_resp["threads"]
    assert any(t["thread_id"] == thread_id for t in threads)

    # Get thread history
    resp = client.get(f"/v1/chat/threads/{thread_id}/history", headers=TEST_HEADERS)
    assert resp.status_code == 200
    history = resp.json()
    assert history["thread_id"] == thread_id
    assert len(history["messages"]) >= 2

    # Feedback endpoint
    last_msg = history["messages"][-1]
    resp = client.post(
        "/v1/chat/feedback",
        json={
            "thread_id": thread_id,
            "message_id": last_msg["message_id"],
            "feedback": "up",
        },
        headers=headers_with_user,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_multiple_blank_thread_creates_distinct_threads(app):
    client = TestClient(app)
    user_id = "testuser_multi"
    headers_with_user = {**TEST_HEADERS, "X-User-Id": user_id}

    # Send first message with blank thread_id
    resp1 = client.post(
        "/v1/chat/completions",
        json={"message": "First message"},
        headers=headers_with_user,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    thread_id1 = data1["thread_id"]

    # Send second message with blank thread_id
    resp2 = client.post(
        "/v1/chat/completions",
        json={"message": "Second message"},
        headers=headers_with_user,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    thread_id2 = data2["thread_id"]

    # The thread IDs should be different
    assert thread_id1 != thread_id2

    # List threads and verify both thread IDs are present
    resp = client.get("/v1/chat/threads", headers=headers_with_user)
    assert resp.status_code == 200
    threads_resp = resp.json()
    threads = threads_resp["threads"]
    thread_ids = {t["thread_id"] for t in threads}
    assert thread_id1 in thread_ids
    assert thread_id2 in thread_ids


@respx.mock
def test_request_id_propagation(app):
    """
    Test that X-Request-Id is properly propagated to downstream services.
    """
    # Arrange
    client = TestClient(app)
    test_request_id = "test-req-id-123"
    user_id = "test-user-for-req-id"

    # Mock the downstream user service
    # The URL must match what's configured in the test_env fixture
    user_service_url = "http://localhost:8001"

    # Mock the get_user_preferences call
    preferences_route = respx.get(
        f"{user_service_url}/v1/internal/users/{user_id}/preferences"
    ).mock(return_value=Response(200, json={"timezone": "UTC"}))

    # Act
    headers = {
        "X-API-Key": TEST_API_KEY,
        "X-Request-Id": test_request_id,
        "X-User-Id": user_id,
    }
    # The /v1/chat/completions endpoint triggers a call to get_user_preferences
    response = client.post(
        "/v1/chat/completions", headers=headers, json={"message": "Hello"}
    )

    # Assert
    assert response.status_code == 200
    assert preferences_route.called, "The downstream service was not called."

    # Check the headers of the request made to the downstream service
    last_request = preferences_route.calls.last.request
    assert last_request.headers.get("x-request-id") == test_request_id
