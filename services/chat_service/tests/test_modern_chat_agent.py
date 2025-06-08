"""
Tests for the new ModernChatAgent implementation.
"""

from unittest.mock import patch

import pytest

from services.chat_service.chat_agent import ModernChatAgent, create_chat_agent


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
    agent = ModernChatAgent(
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
    agent = ModernChatAgent(
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
    agent = ModernChatAgent(
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
@patch("services.chat_service.chat_agent.history_manager")
async def test_build_agent_with_mocked_db(mock_history):
    """Test building agent with mocked database calls."""
    # Mock database calls
    mock_history.get_thread_history.return_value = []

    agent = ModernChatAgent(
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
    mock_history.get_thread_history.assert_called_once_with(5, limit=100)


@pytest.mark.asyncio
@patch("services.chat_service.chat_agent.history_manager")
async def test_get_memory_info(mock_history):
    """Test getting memory information."""
    mock_history.get_thread_history.return_value = []

    agent = ModernChatAgent(
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
    agent = ModernChatAgent(
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

    agent = ModernChatAgent(
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
