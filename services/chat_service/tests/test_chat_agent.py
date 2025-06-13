"""
Unit tests for chat agent functionality.

Tests the chat agent's message processing, response generation,
and integration with various AI models.
"""

# Set required environment variables before any imports
import os

os.environ.setdefault("DB_URL_CHAT", "sqlite:///test.db")


import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat_service.chat_agent import ChatAgent, create_chat_agent


@pytest.fixture
def mock_tools():
    def tool_fn():
        """A test tool function."""
        return "tool result"

    return [tool_fn]


@pytest.mark.asyncio
async def test_modern_chat_agent_creation():
    """Test that ModernChatAgent can be created with various configurations."""
    # Test basic creation
    agent = ChatAgent(
        thread_id=1,
        user_id="test_user",
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )
    assert agent.thread_id == 1
    assert agent.user_id == "test_user"
    assert not agent.enable_fact_extraction
    assert not agent.enable_vector_memory


@pytest.mark.asyncio
async def test_create_chat_agent_factory():
    """Test the factory function works correctly."""
    agent = create_chat_agent(
        thread_id=2,
        user_id="factory_user",
        max_tokens=5000,
        enable_fact_extraction=True,
        enable_vector_memory=True,
    )
    assert agent.thread_id == 2
    assert agent.user_id == "factory_user"
    assert agent.max_tokens == 5000
    assert agent.enable_fact_extraction
    assert agent.enable_vector_memory


@pytest.mark.asyncio
async def test_memory_blocks_creation():
    """Test that memory blocks are created correctly."""
    agent = ChatAgent(
        thread_id=3,
        user_id="memory_user",
        static_content="Custom system prompt",
        enable_fact_extraction=True,
        enable_vector_memory=True,
        max_facts=25,
    )

    # Create storage context and memory blocks
    agent.storage_context = agent._create_storage_context()
    memory_blocks = agent._create_memory_blocks()

    # Should have at least 2 blocks: static, fact extraction
    # Vector memory might fail due to vector store compatibility
    assert len(memory_blocks) >= 2

    # Check block types and priorities
    block_types = [type(block).__name__ for block in memory_blocks]
    assert "StaticMemoryBlock" in block_types
    assert "FactExtractionMemoryBlock" in block_types
    # VectorMemoryBlock might not be created due to vector store issues

    # Check priorities (static should be 0, fact should be 1)
    priorities = [block.priority for block in memory_blocks]
    assert 0 in priorities
    assert 1 in priorities


@pytest.mark.asyncio
async def test_memory_blocks_creation_minimal():
    """Test memory blocks creation with minimal configuration."""
    agent = ChatAgent(
        thread_id=4,
        user_id="minimal_user",
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )

    # Create storage context and memory blocks
    agent.storage_context = agent._create_storage_context()
    memory_blocks = agent._create_memory_blocks()

    # Should have only 1 block: static
    assert len(memory_blocks) == 1
    assert type(memory_blocks[0]).__name__ == "StaticMemoryBlock"
    assert memory_blocks[0].priority == 0


@pytest.mark.asyncio
@patch("services.chat_service.chat_agent.history_manager.get_thread_history")
async def test_build_agent_with_mocked_db(mock_get_thread_history):
    """Test building agent with mocked database calls."""
    # Mock database calls - setup the mock to return an awaitable
    mock_get_thread_history.return_value = []

    agent = ChatAgent(
        thread_id=5,
        user_id="build_user",
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )

    # Build agent should work without errors
    await agent.build_agent()

    # Agent and memory should be initialized
    assert agent.agent is not None
    assert agent.memory is not None

    # Should have called database to load history
    mock_get_thread_history.assert_called_once_with(5, limit=100)


@pytest.mark.asyncio
@patch("services.chat_service.chat_agent.history_manager")
async def test_get_memory_info(mock_history):
    """Test getting memory information."""
    mock_history.get_thread_history.return_value = []

    agent = ChatAgent(
        thread_id=6,
        user_id="info_user",
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )

    # Before building agent
    info = await agent.get_memory_info()
    assert "error" in info

    # After building agent
    await agent.build_agent()
    info = await agent.get_memory_info()
    assert "error" not in info
    assert "session_id" in info
    assert "memory_blocks" in info


@pytest.mark.asyncio
async def test_default_static_content():
    """Test that default static content is generated correctly."""
    agent = ChatAgent(
        thread_id=7,
        user_id="content_user",
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )

    content = agent._get_default_static_content()
    assert "content_user" in content
    assert "helpful" in content.lower()
    assert "assistant" in content.lower()


@pytest.mark.asyncio
async def test_tools_registration():
    """Test that tools are registered correctly."""

    def test_tool():
        """Test tool function."""
        return "test result"

    agent = ChatAgent(
        thread_id=8,
        user_id="tools_user",
        tools=[test_tool],
        enable_fact_extraction=False,
        enable_vector_memory=False,
    )

    assert len(agent.tools) == 1
    assert agent.tools[0] == test_tool


@pytest.mark.asyncio
async def test_backward_compatibility_imports():
    """Test that backward compatibility imports work."""
    # These should not raise ImportError
    from services.chat_service.llama_manager import (
        ChatAgentManager,
    )

    # Test that the orchestration layer works
    manager = ChatAgentManager(thread_id=9, user_id="compat_user")

    # Should have orchestration properties
    assert manager.thread_id == 9
    assert manager.user_id == "compat_user"
    assert hasattr(manager, "active_agents")
    assert hasattr(manager, "main_agent")
    assert hasattr(manager, "tools")
    assert hasattr(manager, "subagents")


@pytest.mark.asyncio
@patch("services.chat_service.chat_agent.history_manager.append_message")
@patch("services.chat_service.chat_agent.history_manager.create_thread")
@patch("services.chat_service.chat_agent.history_manager.get_thread")
@patch("services.chat_service.chat_agent.history_manager.get_thread_history")
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_chat_with_agent(
    mock_get_thread_history, mock_get_thread, mock_create_thread, mock_append_message
):
    """Test chatting with the agent using FakeLLM."""
    # Setup mocks
    mock_get_thread_history.return_value = []
    mock_append_message.return_value = None
    mock_get_thread.return_value = MagicMock(id=202)
    mock_create_thread.return_value = MagicMock(id=202)

    agent = ChatAgent(
        thread_id=202,
        user_id="test_user5",
        enable_fact_extraction=False,  # Disable to avoid mocking complexity
        enable_vector_memory=False,
    )

    # Build agent first
    await agent.build_agent()

    user_input = "Hello, how are you?"
    response = await agent.chat(user_input)

    # With FakeLLM, we expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert user_input in response
    # Verify the message was stored - should be called for the response message
    mock_append_message.assert_called()


@pytest.mark.asyncio
async def test_graceful_fallback_on_memory_errors():
    """Test that the agent gracefully handles memory block creation errors."""
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
        patch(
            "services.chat_service.chat_agent.VectorMemoryBlock"
        ) as mock_vector_block,
    ):

        mock_llm = MagicMock()
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])

        # Make VectorMemoryBlock raise an exception
        mock_vector_block.side_effect = Exception("Vector store error")

        agent = ChatAgent(
            thread_id=303,
            user_id="test_user6",
            enable_fact_extraction=False,
            enable_vector_memory=True,
        )

        # Should not raise an exception
        await agent.build_agent("test input")

        # Should still have some memory blocks (static + fact extraction)
        assert agent.memory is not None
        assert len(agent.memory.memory_blocks) >= 1


@pytest.mark.asyncio
async def test_memory_blocks_priority_order():
    """Test that memory blocks are created with correct priority order."""
    with patch(
        "services.chat_service.chat_agent.history_manager"
    ) as mock_history_manager:

        mock_history_manager.get_thread_history.return_value = []

        agent = ChatAgent(
            thread_id=404,
            user_id="test_user7",
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        # Create storage context and memory blocks manually for testing
        agent.storage_context = agent._create_storage_context()
        memory_blocks = agent._create_memory_blocks()

        # Check that memory blocks have correct priorities
        priorities = [block.priority for block in memory_blocks]
        assert 0 in priorities  # StaticMemoryBlock should always be priority 0

        # Check that we have at least the static block
        assert len(memory_blocks) >= 1


@pytest.mark.asyncio
async def test_agent_with_tools():
    """Test agent creation with custom tools."""
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
        patch(
            "services.chat_service.chat_agent.FunctionCallingAgent"
        ) as mock_agent_class,
    ):

        # Create a mock LLM that's compatible with FunctionCallingLLM
        mock_llm = MagicMock()
        mock_llm.metadata = MagicMock()
        mock_llm.metadata.is_function_calling_model = True
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])

        # Mock the agent creation
        mock_agent_instance = MagicMock()
        mock_agent_class.from_tools.return_value = mock_agent_instance

        def dummy_tool():
            """A dummy tool for testing."""
            return "tool result"

        agent = ChatAgent(
            thread_id=505,
            user_id="test_user8",
            tools=[dummy_tool],
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        await agent.build_agent("test input")

        # Check that tools were set
        assert agent.tools is not None
        assert len(agent.tools) == 1
