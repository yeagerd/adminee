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

            # Test chat
            response = await workflow_agent.chat("Hello")

            assert response == mock_response

            # Verify database calls
            assert mock_history_manager.append_message.call_count == 2
            mock_history_manager.append_message.assert_any_call(
                thread_id=123, user_id="test_user", content="Hello"
            )
            mock_history_manager.append_message.assert_any_call(
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
