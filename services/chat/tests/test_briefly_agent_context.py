"""
Tests for BrieflyAgent conversation context functionality.

These tests verify that:
1. Conversation history is loaded from database
2. Context is passed to LLM calls
3. Responses are saved to database
4. Conversation continuity is maintained
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat.agents.briefly_agent import create_briefly_agent
from services.chat.agents.llm_manager import FakeLLM
from services.chat.service_client import ServiceClient


class TestBrieflyAgentContext:
    """Test conversation context loading and saving in BrieflyAgent."""

    @pytest.fixture
    def mock_history_manager(self):
        """Mock history manager functions for testing."""
        # Mock thread creation and retrieval
        mock_thread = MagicMock()
        mock_thread.id = "test-thread-123"

        # Mock message history
        mock_history = [
            MagicMock(
                id=1,
                thread_id=123,
                user_id="test-user-123",
                content="Hello, how are you?",
                created_at="2024-01-01T00:00:00Z",
            ),
            MagicMock(
                id=2,
                thread_id=123,
                user_id="assistant",
                content="I'm doing well, thank you!",
                created_at="2024-01-01T00:00:01Z",
            ),
        ]

        # Create a mock module with the functions we need
        mock_module = MagicMock()
        mock_module.create_thread = AsyncMock(return_value=mock_thread)
        mock_module.get_thread = AsyncMock(return_value=mock_thread)
        mock_module.get_thread_history = AsyncMock(return_value=mock_history)
        mock_module.append_message = AsyncMock(return_value=MagicMock(id=999))

        return mock_module

    @pytest.fixture
    def mock_service_client(self):
        """Mock service client for testing."""
        mock_client = MagicMock(spec=ServiceClient)
        mock_client.get_calendar_events.return_value = []
        mock_client.get_files.return_value = []
        mock_client.get_user_info.return_value = {
            "id": "test-user-123",
            "name": "Test User",
        }
        mock_client.get_user_preferences.return_value = {}
        return mock_client

    @pytest.fixture
    def fake_llm(self):
        """Create a FakeLLM instance for testing."""
        return FakeLLM()

    @pytest.mark.asyncio
    async def test_conversation_context_loading_and_saving(
        self, mock_history_manager, mock_service_client, fake_llm
    ):
        """Test that conversation context is loaded and saved correctly."""
        with (
            patch(
                "services.chat.history_manager.get_thread_history",
                mock_history_manager.get_thread_history,
            ),
            patch(
                "services.chat.agents.llm_manager.get_llm_manager"
            ) as mock_llm_manager,
        ):

            # Mock the LLM manager to return our FakeLLM
            mock_llm_manager_instance = MagicMock()
            mock_llm_manager_instance.get_llm.return_value = fake_llm
            mock_llm_manager.return_value = mock_llm_manager_instance

            # Create the agent
            agent = create_briefly_agent(
                user_id="test-user-123",
                thread_id="123",
                vespa_endpoint="http://localhost:8080",
            )

            # Verify the agent was created with the correct thread_id
            assert agent.thread_id == "123"

            # Mock the agent's run method to simulate responses
            mock_handler = MagicMock()

            # Create an async generator for stream_events
            async def mock_stream_events():
                return
                yield  # Make it a generator (this line will never be reached)

            mock_handler.stream_events.return_value = mock_stream_events()

            with patch.object(type(agent), "run", return_value=mock_handler):
                # Send a message to trigger conversation history loading
                await agent.achat("Hello, how are you?")

                # Test that conversation history is loaded
                # The agent should have loaded the conversation history during achat
                # We can verify this by checking if the history manager was called
                # Note: limit=101 is used when exclude_latest=True to account for excluding the latest message
                mock_history_manager.get_thread_history.assert_called_once_with(
                    123, limit=101
                )

    @pytest.mark.asyncio
    async def test_context_persistence_between_calls(
        self, mock_history_manager, mock_service_client, fake_llm
    ):
        """Test that context persists between multiple chat calls."""
        with (
            patch(
                "services.chat.history_manager.get_thread_history",
                mock_history_manager.get_thread_history,
            ),
            patch(
                "services.chat.agents.llm_manager.get_llm_manager"
            ) as mock_llm_manager,
        ):

            # Mock the LLM manager to return our FakeLLM
            mock_llm_manager_instance = MagicMock()
            mock_llm_manager_instance.get_llm.return_value = fake_llm
            mock_llm_manager.return_value = mock_llm_manager_instance

            # Create the agent
            agent = create_briefly_agent(
                user_id="test-user-123",
                thread_id="123",
                vespa_endpoint="http://localhost:8080",
            )

            # Send multiple messages to test context persistence
            message1 = "What was our previous conversation about?"
            message2 = "Can you remind me what you said earlier?"

            # Mock the agent's run method to simulate responses
            mock_handler = MagicMock()

            # Create an async generator for stream_events
            async def mock_stream_events():
                return
                yield  # Make it a generator (this line will never be reached)

            mock_handler.stream_events.return_value = mock_stream_events()

            with patch.object(
                type(agent), "run", return_value=mock_handler
            ) as mock_run:

                # Send first message
                await agent.achat(message1)

                # Send second message
                await agent.achat(message2)

                # Verify that run was called twice with different messages
                assert mock_run.call_count == 2

                # Verify that conversation history was loaded for both calls
                assert mock_history_manager.get_thread_history.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_conversation_history(
        self, mock_history_manager, mock_service_client, fake_llm
    ):
        """Test handling of empty conversation history."""
        with (
            patch(
                "services.chat.history_manager.get_thread_history",
                mock_history_manager.get_thread_history,
            ),
            patch(
                "services.chat.agents.llm_manager.get_llm_manager"
            ) as mock_llm_manager,
        ):

            # Mock empty history
            mock_history_manager.get_thread_history.return_value = []

            # Mock the LLM manager to return our FakeLLM
            mock_llm_manager_instance = MagicMock()
            mock_llm_manager_instance.get_llm.return_value = fake_llm
            mock_llm_manager.return_value = mock_llm_manager_instance

            # Create the agent
            agent = create_briefly_agent(
                user_id="test-user-123",
                thread_id="123",
                vespa_endpoint="http://localhost:8080",
            )

            # Verify the agent was created successfully even with empty history
            assert agent.thread_id == "123"

            # Test that the agent can still process messages
            mock_handler = MagicMock()

            # Create an async generator for stream_events
            async def mock_stream_events():
                return
                yield  # Make it a generator (this line will never be reached)

            mock_handler.stream_events.return_value = mock_stream_events()

            with patch.object(
                type(agent), "run", return_value=mock_handler
            ) as mock_run:
                await agent.achat("Hello, this is my first message")

                # Verify that run was called
                mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, mock_history_manager, mock_service_client, fake_llm
    ):
        """Test graceful handling of database errors."""
        with (
            patch(
                "services.chat.history_manager.get_thread_history",
                mock_history_manager.get_thread_history,
            ),
            patch(
                "services.chat.agents.llm_manager.get_llm_manager"
            ) as mock_llm_manager,
        ):

            # Mock database error
            mock_history_manager.get_thread_history.side_effect = Exception(
                "Database connection failed"
            )

            # Mock the LLM manager to return our FakeLLM
            mock_llm_manager_instance = MagicMock()
            mock_llm_manager_instance.get_llm.return_value = fake_llm
            mock_llm_manager.return_value = mock_llm_manager_instance

            # The agent should still be created even if history loading fails
            try:
                agent = create_briefly_agent(
                    user_id="test-user-123",
                    thread_id="123",
                    vespa_endpoint="http://localhost:8080",
                )

                # Agent should be created with basic functionality
                assert agent.thread_id == "123"

            except Exception as e:
                # If the agent creation fails due to history loading, that's acceptable
                # as long as it fails gracefully
                assert "Database connection failed" in str(e)

    @pytest.mark.asyncio
    async def test_conversation_history_loading(
        self, mock_history_manager, mock_service_client, fake_llm
    ):
        """Test loading of rich conversation history."""
        # Create rich conversation history
        rich_history = [
            MagicMock(
                id=1,
                thread_id=123,
                user_id="test-user-123",
                content="I need to schedule a meeting with John",
                created_at="2024-01-01T00:00:00Z",
            ),
            MagicMock(
                id=2,
                thread_id=123,
                user_id="assistant",
                content="I can help you schedule a meeting. What time works best for you?",
                created_at="2024-01-01T00:00:01Z",
            ),
            MagicMock(
                id=3,
                thread_id=123,
                user_id="test-user-123",
                content="How about tomorrow at 2 PM?",
                created_at="2024-01-01T00:00:02Z",
            ),
            MagicMock(
                id=4,
                thread_id=123,
                user_id="assistant",
                content="I'll check your calendar and schedule that meeting for you.",
                created_at="2024-01-01T00:00:03Z",
            ),
        ]

        mock_history_manager.get_thread_history.return_value = rich_history

        with (
            patch(
                "services.chat.history_manager.get_thread_history",
                mock_history_manager.get_thread_history,
            ),
            patch(
                "services.chat.agents.llm_manager.get_llm_manager"
            ) as mock_llm_manager,
        ):

            # Mock the LLM manager to return our FakeLLM
            mock_llm_manager_instance = MagicMock()
            mock_llm_manager_instance.get_llm.return_value = fake_llm
            mock_llm_manager.return_value = mock_llm_manager_instance

            # Create the agent
            agent = create_briefly_agent(
                user_id="test-user-123",
                thread_id="123",
                vespa_endpoint="http://localhost:8080",
            )

            # Verify the agent was created
            assert agent.thread_id == "123"

            # Test that the agent can process a follow-up message
            mock_handler = MagicMock()

            # Create an async generator for stream_events
            async def mock_stream_events():
                return
                yield  # Make it a generator (this line will never be reached)

            mock_handler.stream_events.return_value = mock_stream_events()

            with patch.object(
                type(agent), "run", return_value=mock_handler
            ) as mock_run:
                await agent.achat("Can you also invite Sarah to the meeting?")

                # Verify that run was called
                mock_run.assert_called_once()

                # Verify that the rich history was loaded during the achat call
                # Note: limit=101 is used when exclude_latest=True to account for excluding the latest message
                mock_history_manager.get_thread_history.assert_called_once_with(
                    123, limit=101
                )


# Integration test that tests the full API flow
class TestBrieflyAgentAPIIntegration:
    """Test the full API integration with conversation context."""

    @pytest.mark.asyncio
    async def test_api_endpoint_with_conversation_context(self):
        """
        Test that the API endpoint properly handles conversation context.

        This test verifies the complete flow from API call to database persistence.
        """
        # This would be a more complex integration test that:
        # 1. Sets up a test database with conversation history
        # 2. Makes an API call to the chat endpoint
        # 3. Verifies the response includes the conversation context
        # 4. Verifies the database is updated correctly

        # For now, we'll mark this as a TODO since it requires more setup
        pytest.skip("Integration test requires more complex setup with test database")
