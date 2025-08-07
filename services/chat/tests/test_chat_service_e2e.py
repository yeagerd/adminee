"""
End-to-end tests for chat service with multi-agent workflow.

Tests the complete chat service functionality including
multi-agent workflow processing, history management, and API endpoints.
"""

import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set up test settings before any imports
import services.chat.settings as chat_settings
from services.chat.tests.test_base import BaseChatTest

# Create test settings instance
test_settings = chat_settings.Settings(
    db_url_chat="sqlite+aiosqlite:///file::memory:?cache=shared",
    api_frontend_chat_key="test-frontend-chat-key",
    api_chat_user_key="test-chat-user-key",
    api_chat_office_key="test-chat-office-key",
    user_service_url="http://localhost:8001",
    office_service_url="http://localhost:8003",
    pagination_secret_key="test-pagination-secret-key",
)

# Set the test settings as the singleton
chat_settings._settings = test_settings

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
    }
    with patch.dict("os.environ", env_vars):
        yield env_vars


class TestChatServiceE2E(BaseChatTest):
    @classmethod
    def setup_class(cls):
        # Set up environment variables
        env_vars = {
            "DB_URL_CHAT": "sqlite+aiosqlite:///file::memory:?cache=shared",
            # Don't set OPENAI_API_KEY so it falls back to FakeLLM
            "LLM_MODEL": "fake-model",
            "LLM_PROVIDER": "fake",
        }
        patcher = patch.dict("os.environ", env_vars)
        patcher.start()
        cls._env_patcher = patcher
        # Force reload the auth module to pick up the new settings
        for module in list(sys.modules):
            if module.startswith("services.chat"):
                del sys.modules[module]
        import services.chat.settings as chat_settings
        from services.chat import history_manager
        from services.chat.main import app as fresh_app

        test_settings = chat_settings.Settings(
            db_url_chat="sqlite+aiosqlite:///file::memory:?cache=shared",
            api_frontend_chat_key="test-frontend-chat-key",
            api_chat_user_key="test-chat-user-key",
            api_chat_office_key="test-chat-office-key",
            user_service_url="http://localhost:8001",
            office_service_url="http://localhost:8003",
            pagination_secret_key="test-pagination-secret-key",
        )
        chat_settings._settings = test_settings
        cls._history_manager = history_manager
        cls.app = fresh_app
        # Initialize test database synchronously

        # Database should be initialized via Alembic migrations before running tests

    # Run: alembic upgrade head

    @classmethod
    def teardown_class(cls):
        if hasattr(cls, "_env_patcher"):
            cls._env_patcher.stop()

    def test_end_to_end_chat_flow(self):
        client = TestClient(self.app)
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

    def test_multiple_blank_thread_creates_distinct_threads(self):
        client = TestClient(self.app)
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

    def test_request_id_propagation(self):
        """
        Test that X-Request-Id is properly propagated to downstream services.
        """
        # Arrange
        test_request_id = "test-req-id-123"
        user_id = "test-user-for-req-id"

        # Mock the downstream user service using unittest.mock
        # Create a mock response
        from unittest.mock import AsyncMock, MagicMock, patch

        import httpx

        from services.common.logging_config import request_id_var

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"timezone": "UTC"}

        # Mock the httpx.AsyncClient.get method to return the mock response
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            # Set the request ID in the context
            request_id_var.set(test_request_id)

            # Act - test the ServiceClient directly
            import asyncio

            from services.chat.service_client import ServiceClient

            async def test_service_client():
                async with ServiceClient() as service_client:
                    await service_client.get_user_preferences(user_id)

            # Run the async function
            asyncio.run(test_service_client())

            # Assert
            assert mock_get.called, "The downstream service was not called."

            # Check that the request was made with the correct URL
            call_args = mock_get.call_args
            assert call_args is not None
            url = call_args[0][0]  # First positional argument is the URL
            assert f"/v1/internal/users/{user_id}/preferences" in url

            # Check the headers
            headers = call_args[1].get("headers", {})  # Keyword arguments
            assert headers.get("X-Request-Id") == test_request_id
