"""
Tests for the modern chat agent with explicit memory blocks.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat_service.chat_agent import ChatAgent, create_chat_agent


@pytest.mark.asyncio
async def test_create_modern_chat_agent():
    """Test creating a modern chat agent using the factory function."""
    with patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager:
        mock_llm_manager.return_value = MagicMock()

        agent = create_chat_agent(
            thread_id=123,
            user_id="test_user",
            max_tokens=1000,
            tools=[],
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        assert isinstance(agent, ChatAgent)
        assert agent.thread_id == 123
        assert agent.user_id == "test_user"
        assert agent.max_tokens == 1000
        assert agent.enable_fact_extraction
        assert agent.enable_vector_memory


@pytest.mark.asyncio
async def test_chat_agent_initialization():
    """Test ChatAgent initialization with modern memory blocks."""
    with patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager:
        mock_llm_manager.return_value = MagicMock()

        agent = ChatAgent(
            thread_id=456,
            user_id="test_user2",
            max_tokens=2000,
            tools=[],
            enable_fact_extraction=False,
            enable_vector_memory=True,
        )

        assert agent.thread_id == 456
        assert agent.user_id == "test_user2"
        assert agent.max_tokens == 2000
        assert not agent.enable_fact_extraction
        assert agent.enable_vector_memory


@pytest.mark.asyncio
async def test_build_agent_creates_memory_blocks():
    """Test that build_agent creates the appropriate memory blocks."""
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
    ):

        mock_llm = MagicMock()
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])

        agent = ChatAgent(
            thread_id=789,
            user_id="test_user3",
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        await agent.build_agent("test input")

        # Check that memory blocks were created
        assert agent.memory is not None
        assert len(agent.memory.memory_blocks) > 0

        # Check that the agent was built
        assert agent.agent is not None


@pytest.mark.asyncio
async def test_get_memory_info_returns_blocks():
    """Test that get_memory_info returns information about memory blocks."""
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
    ):

        mock_llm = MagicMock()
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])

        agent = ChatAgent(
            thread_id=101,
            user_id="test_user4",
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        await agent.build_agent("test input")
        memory_info = await agent.get_memory_info()

        assert isinstance(memory_info, dict)
        assert "memory_blocks" in memory_info
        assert len(memory_info["memory_blocks"]) > 0

        # Check that each memory block info has the expected structure
        for block_info in memory_info["memory_blocks"]:
            assert "type" in block_info
            assert "priority" in block_info


@pytest.mark.asyncio
async def test_chat_with_agent():
    """Test chatting with the agent."""
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
    ):

        mock_llm = MagicMock()
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])
        mock_history_manager.append_message = AsyncMock()
        mock_history_manager.Thread = MagicMock()
        mock_history_manager.Thread.objects = MagicMock()
        mock_history_manager.Thread.objects.get = AsyncMock(
            return_value=MagicMock(id=202)
        )

        agent = ChatAgent(
            thread_id=202,
            user_id="test_user5",
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        # Mock the agent's achat method
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "Test response"
        mock_agent.achat = AsyncMock(return_value=mock_response)
        agent.agent = mock_agent

        response = await agent.chat("Hello, how are you?")

        assert response == "Test response"
        mock_agent.achat.assert_called_once_with("Hello, how are you?")


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
    with (
        patch("services.chat_service.chat_agent.llm_manager") as mock_llm_manager,
        patch(
            "services.chat_service.chat_agent.history_manager"
        ) as mock_history_manager,
        patch(
            "services.chat_service.chat_agent.FactExtractionMemoryBlock"
        ) as mock_fact_block,
        patch(
            "services.chat_service.chat_agent.VectorMemoryBlock"
        ) as mock_vector_block,
    ):

        mock_llm = MagicMock()
        mock_llm_manager.return_value = mock_llm
        mock_history_manager.get_conversation_history = AsyncMock(return_value=[])

        # Mock memory blocks with proper priority
        mock_fact_instance = MagicMock()
        mock_fact_instance.priority = 1
        mock_fact_block.return_value = mock_fact_instance

        mock_vector_instance = MagicMock()
        mock_vector_instance.priority = 2
        mock_vector_block.return_value = mock_vector_instance

        agent = ChatAgent(
            thread_id=404,
            user_id="test_user7",
            enable_fact_extraction=True,
            enable_vector_memory=True,
        )

        await agent.build_agent("test input")

        # Check that memory blocks have correct priorities
        priorities = [block.priority for block in agent.memory.memory_blocks]
        assert 0 in priorities  # StaticMemoryBlock
        assert 1 in priorities  # FactExtractionMemoryBlock
        assert 2 in priorities  # VectorMemoryBlock


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
