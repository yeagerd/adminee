"""
Tests for BrieflyAgent conversation context functionality.

These tests verify that:
1. Conversation history is loaded from database
2. Context is passed to LLM calls
3. Responses are saved to database
4. Conversation continuity is maintained
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBrieflyAgentContext:
    """Test conversation context functionality in BrieflyAgent."""

    @pytest.mark.asyncio
    async def test_conversation_context_loading_and_saving(self):
        """
        Test that conversation context is loaded from DB, passed to LLM, and saved back.
        
        This test verifies the complete flow:
        1. Send a chat request via API
        2. Patch the DB load to have expected conversation context
        3. Expect a patched LLM call with that context
        4. Return a patched response
        5. Expect a DB save for both user message and assistant response
        """
        from fastapi.testclient import TestClient
        from services.chat.main import app
        
        client = TestClient(app)
        user_id = "test_context_user"
        thread_id = "12345"
        headers = {"X-API-Key": "test-frontend-chat-key", "X-User-Id": user_id}
        
        # Mock conversation history from database
        mock_conversation_history = [
            MagicMock(
                user_id=user_id,
                content="Hello, I'm working on a Python project",
                created_at="2023-01-01T10:00:00"
            ),
            MagicMock(
                user_id="assistant", 
                content="Great! I'd be happy to help you with your Python project. What specific aspect are you working on?",
                created_at="2023-01-01T10:00:01"
            ),
            MagicMock(
                user_id=user_id,
                content="I need help with testing",
                created_at="2023-01-01T10:00:02"
            )
        ]
        
        # Mock the history manager for database operations
        with patch("services.chat.history_manager") as mock_history:
            # Set up the mock to return our conversation history
            mock_history.get_thread_history = AsyncMock(return_value=mock_conversation_history)
            mock_history.append_message = AsyncMock(return_value=MagicMock(id=999))
            mock_history.get_or_create_thread = AsyncMock(return_value=MagicMock(id=int(thread_id)))
            mock_history.get_thread = AsyncMock(return_value=MagicMock(id=int(thread_id), user_id=user_id))
            
            # Mock the LLM to return a context-aware response
            with patch("services.chat.agents.briefly_agent.get_llm_manager") as mock_llm_manager:
                mock_llm = MagicMock()
                mock_llm.chat = AsyncMock(return_value="I remember you're working on a Python project and need help with testing! Let me help you write some unit tests.")
                mock_llm_manager.return_value.get_llm.return_value = mock_llm
                
                # Mock the ServiceClient to avoid HTTP errors in tests
                with patch("services.chat.api.ServiceClient") as mock_service_client_class:
                    mock_service_client = AsyncMock()
                    mock_service_client.get_user_preferences = AsyncMock(return_value={})
                    mock_service_client_class.return_value.__aenter__.return_value = mock_service_client
                    
                    # Act: Send a chat request (without thread_id to create new thread)
                    user_message = "Can you help me write a test for my function?"
                    response = client.post(
                        "/v1/chat/completions",
                        json={"message": user_message},
                        headers=headers
                    )
        
        # Assert: Verify the API call was successful
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        response_data = response.json()
        
        # Assert: Verify we got a context-aware response
        assistant_response = response_data["messages"][-1]["content"]
        assert "I remember you're working on a Python project" in assistant_response
        assert "testing" in assistant_response
        
        # Assert: Verify conversation history was loaded from database
        mock_history.get_thread_history.assert_called()
        
        # Assert: Verify user message was saved to database
        user_message_calls = [call for call in mock_history.append_message.call_args_list 
                             if call[1].get("content") == user_message]
        assert len(user_message_calls) >= 1, "User message should be saved to database"
        
        # Assert: Verify assistant response was saved to database
        assistant_message_calls = [call for call in mock_history.append_message.call_args_list 
                                  if call[1].get("user_id") == "assistant"]
        assert len(assistant_message_calls) >= 1, "Assistant response should be saved to database"
        
        # Assert: Verify the LLM was called (conversation context was passed)
        mock_llm.chat.assert_called_once()
        
        # Note: The actual context passed to the LLM is handled by LlamaIndex internally,
        # but we can verify that the conversation history loading was triggered

    @pytest.mark.asyncio
    async def test_conversation_context_persistence_between_calls(self):
        """Test that conversation context persists between multiple chat calls."""
        from fastapi.testclient import TestClient
        from services.chat.main import app
        
        client = TestClient(app)
        user_id = "test_persistence_user"
        thread_id = "54321"
        headers = {"X-API-Key": "test-frontend-chat-key", "X-User-Id": user_id}
        
        # Mock the history manager for database operations
        with patch("services.chat.history_manager") as mock_history:
            # Initially empty conversation
            conversation_messages = []
            
            def mock_get_thread_history(*args, **kwargs):
                return list(reversed(conversation_messages))  # Return chronological order
            
            def mock_append_message(*args, **kwargs):
                # Simulate adding message to conversation
                message_data = kwargs
                mock_msg = MagicMock()
                mock_msg.id = len(conversation_messages) + 1
                mock_msg.user_id = message_data.get("user_id")
                mock_msg.content = message_data.get("content")
                mock_msg.created_at = f"2023-01-01T10:00:{len(conversation_messages):02d}"
                conversation_messages.append(mock_msg)
                return mock_msg
            
            mock_history.get_thread_history = AsyncMock(side_effect=mock_get_thread_history)
            mock_history.append_message = AsyncMock(side_effect=mock_append_message)
            mock_history.get_or_create_thread = AsyncMock(return_value=MagicMock(id=int(thread_id)))
            
            # Mock the LLM to return context-aware responses
            with patch("services.chat.agents.briefly_agent.get_llm_manager") as mock_llm_manager:
                mock_llm = MagicMock()
                
                # First response
                def mock_chat_first(*args, **kwargs):
                    return "Hello! I'm here to help you with your questions."
                
                # Second response (should show awareness of first interaction)
                def mock_chat_second(*args, **kwargs):
                    return "As I mentioned before, I'm here to help. What specific question do you have?"
                
                mock_llm.chat = AsyncMock(side_effect=[mock_chat_first(), mock_chat_second()])
                mock_llm_manager.return_value.get_llm.return_value = mock_llm
                
                # Mock the ServiceClient to avoid HTTP errors in tests
                with patch("services.chat.api.ServiceClient") as mock_service_client_class:
                    mock_service_client = AsyncMock()
                    mock_service_client.get_user_preferences = AsyncMock(return_value={})
                    mock_service_client_class.return_value.__aenter__.return_value = mock_service_client
                    
                    # Act: First chat message
                    first_message = "Hello, can you help me?"
                    response1 = client.post(
                        "/v1/chat/completions",
                        json={"thread_id": thread_id, "message": first_message},
                        headers=headers
                    )
                    
                    # Act: Second chat message in same thread
                    second_message = "What can you do?"
                    response2 = client.post(
                        "/v1/chat/completions",
                        json={"thread_id": thread_id, "message": second_message},
                        headers=headers
                    )
        
        # Assert: Both API calls were successful
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Assert: Verify conversation history was loaded for both calls
        assert mock_history.get_thread_history.call_count == 2
        
        # Assert: Verify both user messages and assistant responses were saved
        assert mock_history.append_message.call_count == 4  # 2 user + 2 assistant
        
        # Assert: Verify the messages are in the simulated conversation
        assert len(conversation_messages) == 4
        assert conversation_messages[0].content == first_message
        assert conversation_messages[1].user_id == "assistant"
        assert conversation_messages[2].content == second_message
        assert conversation_messages[3].user_id == "assistant"
        
        # Assert: Verify LLM was called twice
        assert mock_llm.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_conversation_history(self):
        """Test behavior when there's no conversation history."""
        from fastapi.testclient import TestClient
        from services.chat.main import app
        
        client = TestClient(app)
        user_id = "test_empty_history_user"
        thread_id = "99999"
        headers = {"X-API-Key": "test-frontend-chat-key", "X-User-Id": user_id}
        
        # Mock the history manager for database operations
        with patch("services.chat.history_manager") as mock_history:
            # Return empty conversation history
            mock_history.get_thread_history = AsyncMock(return_value=[])
            mock_history.append_message = AsyncMock(return_value=MagicMock(id=1))
            mock_history.get_or_create_thread = AsyncMock(return_value=MagicMock(id=int(thread_id)))
            
            # Mock the LLM to return a fresh conversation response
            with patch("services.chat.agents.briefly_agent.get_llm_manager") as mock_llm_manager:
                mock_llm = MagicMock()
                mock_llm.chat = AsyncMock(return_value="Hello! I'm Briefly, your AI assistant. How can I help you today?")
                mock_llm_manager.return_value.get_llm.return_value = mock_llm
                
                # Mock the ServiceClient to avoid HTTP errors in tests
                with patch("services.chat.api.ServiceClient") as mock_service_client_class:
                    mock_service_client = AsyncMock()
                    mock_service_client.get_user_preferences = AsyncMock(return_value={})
                    mock_service_client_class.return_value.__aenter__.return_value = mock_service_client
                    
                    # Act: Send first message in new conversation
                    user_message = "Hi there!"
                    response = client.post(
                        "/v1/chat/completions",
                        json={"thread_id": thread_id, "message": user_message},
                        headers=headers
                    )
        
        # Assert: API call was successful
        assert response.status_code == 200
        response_data = response.json()
        
        # Assert: Verify we got a fresh conversation response
        assistant_response = response_data["messages"][-1]["content"]
        assert "Hello!" in assistant_response or "Hi" in assistant_response
        
        # Assert: Verify empty conversation history was handled gracefully
        mock_history.get_thread_history.assert_called()
        
        # Assert: Verify user message was saved despite empty history
        mock_history.append_message.assert_called()
        
        # Assert: Verify LLM was called even with empty context
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test that the agent continues working even if database operations fail."""
        from fastapi.testclient import TestClient
        from services.chat.main import app
        
        client = TestClient(app)
        user_id = "test_db_error_user"
        thread_id = "88888"
        headers = {"X-API-Key": "test-frontend-chat-key", "X-User-Id": user_id}
        
        # Mock the history manager to simulate database errors
        with patch("services.chat.history_manager") as mock_history:
            # Simulate database errors for history loading and saving
            mock_history.get_thread_history = AsyncMock(side_effect=Exception("Database connection failed"))
            mock_history.append_message = AsyncMock(side_effect=Exception("Database write failed"))
            mock_history.get_or_create_thread = AsyncMock(return_value=MagicMock(id=int(thread_id)))
            
            # Mock the LLM to return a normal response
            with patch("services.chat.agents.briefly_agent.get_llm_manager") as mock_llm_manager:
                mock_llm = MagicMock()
                mock_llm.chat = AsyncMock(return_value="I can still help you even if there are database issues!")
                mock_llm_manager.return_value.get_llm.return_value = mock_llm
                
                # Mock the ServiceClient to avoid HTTP errors in tests
                with patch("services.chat.api.ServiceClient") as mock_service_client_class:
                    mock_service_client = AsyncMock()
                    mock_service_client.get_user_preferences = AsyncMock(return_value={})
                    mock_service_client_class.return_value.__aenter__.return_value = mock_service_client
                    
                    # Act: Send a chat message despite database errors
                    user_message = "Can you help me?"
                    response = client.post(
                        "/v1/chat/completions",
                        json={"thread_id": thread_id, "message": user_message},
                        headers=headers
                    )
        
        # Assert: API call should still succeed despite database errors
        assert response.status_code == 200
        response_data = response.json()
        
        # Assert: Verify we still got a response from the LLM
        assistant_response = response_data["messages"][-1]["content"]
        assert "I can still help you" in assistant_response
        
        # Assert: Verify database operations were attempted but failed gracefully
        mock_history.get_thread_history.assert_called()
        
        # Note: The API should handle database errors gracefully and continue processing
        # The conversation should work even if history loading/saving fails

    @pytest.mark.asyncio
    async def test_conversation_history_loading(self):
        """Test that conversation history is properly loaded and formatted."""
        from fastapi.testclient import TestClient
        from services.chat.main import app
        
        client = TestClient(app)
        user_id = "test_history_loading_user"
        thread_id = "77777"
        headers = {"X-API-Key": "test-frontend-chat-key", "X-User-Id": user_id}
        
        # Create a rich conversation history with different message types
        mock_conversation_history = [
            MagicMock(
                user_id=user_id,
                content="Hello, I'm new to Python programming",
                created_at="2023-01-01T10:00:00"
            ),
            MagicMock(
                user_id="assistant",
                content="Welcome to Python! It's a great language to learn. What would you like to start with?",
                created_at="2023-01-01T10:00:01"
            ),
            MagicMock(
                user_id=user_id,
                content="I want to learn about functions",
                created_at="2023-01-01T10:00:02"
            ),
            MagicMock(
                user_id="assistant",
                content="Functions are fundamental in Python! Let me explain how they work...",
                created_at="2023-01-01T10:00:03"
            ),
            MagicMock(
                user_id=user_id,
                content="Can you show me an example?",
                created_at="2023-01-01T10:00:04"
            )
        ]
        
        # Mock the history manager for database operations
        with patch("services.chat.history_manager") as mock_history:
            mock_history.get_thread_history = AsyncMock(return_value=mock_conversation_history)
            mock_history.append_message = AsyncMock(return_value=MagicMock(id=999))
            mock_history.get_or_create_thread = AsyncMock(return_value=MagicMock(id=int(thread_id)))
            
            # Mock the LLM to return a context-aware response
            with patch("services.chat.agents.briefly_agent.get_llm_manager") as mock_llm_manager:
                mock_llm = MagicMock()
                mock_llm.chat = AsyncMock(return_value="Of course! Here's a simple Python function example: def greet(name): return f'Hello, {name}!'")
                mock_llm_manager.return_value.get_llm.return_value = mock_llm
                
                # Mock the ServiceClient to avoid HTTP errors in tests
                with patch("services.chat.api.ServiceClient") as mock_service_client_class:
                    mock_service_client = AsyncMock()
                    mock_service_client.get_user_preferences = AsyncMock(return_value={})
                    mock_service_client_class.return_value.__aenter__.return_value = mock_service_client
                    
                    # Act: Send a follow-up message
                    user_message = "That's helpful, thank you!"
                    response = client.post(
                        "/v1/chat/completions",
                        json={"thread_id": thread_id, "message": user_message},
                        headers=headers
                    )
        
        # Assert: API call was successful
        assert response.status_code == 200
        response_data = response.json()
        
        # Assert: Verify we got a response
        assistant_response = response_data["messages"][-1]["content"]
        assert "function" in assistant_response.lower()
        
        # Assert: Verify conversation history was loaded
        mock_history.get_thread_history.assert_called_once_with(thread_id, limit=100)
        
        # Assert: Verify the rich conversation history was processed
        # (The agent should have loaded all 5 previous messages)
        get_history_call = mock_history.get_thread_history.call_args_list[0]
        assert get_history_call[0][0] == thread_id  # First positional arg should be thread_id
        
        # Assert: Verify user message and assistant response were saved
        assert mock_history.append_message.call_count >= 2  # At least user message + assistant response
        
        # Assert: Verify LLM was called with the loaded context
        mock_llm.chat.assert_called_once()
        
        # Note: The actual conversation context formatting is handled internally by LlamaIndex,
        # but we can verify that the history loading mechanism was triggered correctly


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
