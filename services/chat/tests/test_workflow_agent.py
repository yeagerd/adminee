"""
Tests for WorkflowAgent implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat.agents.workflow_agent import WorkflowAgent


@pytest.fixture
def mock_history_manager():
    """Mock the history manager."""
    with patch("services.chat.agents.workflow_agent.history_manager") as mock:
        mock.append_message = AsyncMock()
        mock.get_thread_history = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def workflow_agent(mock_history_manager):
    """Create a WorkflowAgent instance for testing."""
    return WorkflowAgent(
        thread_id=123,
        user_id="test_user",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=1000,
    )


def test_workflow_agent_initialization(workflow_agent):
    """Test WorkflowAgent initializes correctly."""
    assert workflow_agent.thread_id == 123
    assert workflow_agent.user_id == "test_user"
    assert workflow_agent.llm_model == "fake-model"
    assert workflow_agent.llm_provider == "fake"
    assert workflow_agent.max_tokens == 1000

    # Check that components are None initially
    assert workflow_agent.agent_workflow is None
    assert workflow_agent.context is None
    assert workflow_agent.specialized_agents == {}

    # Check that LLM is created
    assert workflow_agent._llm is not None


def test_prepare_tools(workflow_agent):
    """Test tool preparation handles different tool types."""
    from llama_index.core.tools import FunctionTool

    # Test with no tools
    tools = workflow_agent._prepare_tools(None)
    assert tools == []

    # Test with empty list
    tools = workflow_agent._prepare_tools([])
    assert tools == []

    # Test with a simple function
    def test_func():
        return "test"

    tools = workflow_agent._prepare_tools([test_func])
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)

    # Test with existing FunctionTool
    existing_tool = FunctionTool.from_defaults(fn=test_func)
    tools = workflow_agent._prepare_tools([existing_tool])
    assert len(tools) == 1
    assert tools[0] is existing_tool


@pytest.mark.asyncio
async def test_build_agent(workflow_agent, mock_history_manager):
    """Test agent building process."""
    # Mock the database history loading
    with patch.object(
        workflow_agent, "_load_chat_history_from_db", new_callable=AsyncMock
    ) as mock_history:
        mock_history.return_value = []

        await workflow_agent.build_agent("test input")

        # Check that components are initialized
        assert workflow_agent.agent_workflow is not None
        assert workflow_agent.context is not None
        assert len(workflow_agent.specialized_agents) > 0


@pytest.mark.asyncio
async def test_chat_basic_flow(workflow_agent, mock_history_manager):
    """Test basic chat functionality."""
    # Mock the agent workflow
    mock_response = "Test response"

    with patch.object(workflow_agent, "build_agent", new_callable=AsyncMock):
        # Create mock workflow and context
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value=mock_response)
        workflow_agent.agent_workflow = mock_workflow

        mock_context = MagicMock()
        workflow_agent.context = mock_context

        # Mock database history loading
        with patch.object(
            workflow_agent, "_load_chat_history_from_db", new_callable=AsyncMock
        ) as mock_history:
            mock_history.return_value = []

            # Mock the history_manager import inside the chat method
            with patch("services.chat.history_manager") as mock_hm:
                mock_hm.append_message = AsyncMock()

                # Test chat
                response = await workflow_agent.chat("Hello")

                assert response == mock_response

                # Verify database calls
                assert mock_hm.append_message.call_count == 2
                mock_hm.append_message.assert_any_call(
                    thread_id=123, user_id="test_user", content="Hello"
                )
                mock_hm.append_message.assert_any_call(
                    thread_id=123, user_id="assistant", content=mock_response
                )


@pytest.mark.asyncio
async def test_memory_methods(workflow_agent):
    """Test memory-related methods."""
    # Test get_memory_info - should return workflow state info
    info = await workflow_agent.get_memory_info()
    assert isinstance(info, dict)
    assert "workflow_context" in info
    assert "specialized_agents" in info

    # Test reset_memory - should reset workflow state
    await workflow_agent.reset_memory()
    # Should complete without error


def test_llm_property(workflow_agent):
    """Test LLM property access."""
    # The LLM should be initialized
    llm = workflow_agent.llm
    assert llm is not None

    # Subsequent calls should return the same instance
    llm2 = workflow_agent.llm
    assert llm is llm2


def test_compatibility_properties(workflow_agent):
    """Test properties for compatibility with existing code."""
    # Test memory property - should return workflow context (None until built)
    memory = workflow_agent.memory
    assert memory is None  # Context is None until build_agent is called

    # Test agent property - should return None until built
    agent = workflow_agent.agent
    assert agent is None  # Coordinator agent is None until build_agent is called


@pytest.mark.asyncio
async def test_load_conversation_history(workflow_agent, mock_history_manager):
    """Test loading conversation history into workflow context."""
    # 1. Setup mock context
    mock_context = MagicMock()
    mock_context.get = AsyncMock(return_value={})  # Simulate current state is empty
    mock_context.store = MagicMock()
    mock_context.store.set = AsyncMock()
    workflow_agent.context = mock_context

    # 2. Mock _load_chat_history_from_db
    # The method expects a list of objects that can be accessed with msg['role'] and msg['content']
    mock_db_history = [
        {
            "role": "USER",
            "content": "Hello there!",
            "user_id": "test_user",
            "created_at": "2023-01-01T10:00:00",
        },
        {
            "role": "ASSISTANT",
            "content": "Hi, how can I help?",
            "user_id": "assistant",
            "created_at": "2023-01-01T10:00:30",
        },
        {
            "role": "User",
            "content": "Tell me a joke.",
            "user_id": "test_user",
            "created_at": "2023-01-01T10:01:00",
        },
    ]
    workflow_agent._load_chat_history_from_db = AsyncMock(return_value=mock_db_history)

    # 3. Call the method
    await workflow_agent._load_conversation_history()

    # 4. Assertions
    workflow_agent._load_chat_history_from_db.assert_called_once()

    # Assert context.get was called to fetch the current state
    mock_context.get.assert_called_once_with("state", {})

    # Assert context.store.set was called with the correctly formatted history
    expected_formatted_history = [
        {"role": "user", "content": "Hello there!"},
        {"role": "assistant", "content": "Hi, how can I help?"},
        {"role": "user", "content": "Tell me a joke."},
    ]

    # The actual call to set will be like: mock_context.store.set('state', {'conversation_history': [...]})
    # We need to check the arguments of the call
    args, kwargs = mock_context.store.set.call_args
    assert args[0] == "state"  # First positional argument is 'state'
    assert (
        "conversation_history" in args[1]
    )  # Second positional argument is the state dictionary
    actual_history_set = args[1]["conversation_history"]

    assert actual_history_set == expected_formatted_history
    mock_context.store.set.assert_called_once()


@pytest.mark.asyncio
async def test_load_conversation_history_no_context(workflow_agent):
    """Test _load_conversation_history when context is None."""
    workflow_agent.context = None
    workflow_agent._load_chat_history_from_db = AsyncMock()

    await workflow_agent._load_conversation_history()

    workflow_agent._load_chat_history_from_db.assert_not_called()
