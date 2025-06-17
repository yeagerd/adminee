"""
Unit tests for Llama manager functionality.

Tests Llama model integration, response generation,
and model management operations.
"""

# Set required environment variables before any imports
import os

os.environ.setdefault("DB_URL_CHAT", "sqlite:///test.db")


import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat.llama_manager import ChatAgentManager


@pytest.fixture
def mock_llm():
    return MagicMock(name="llm")


@pytest.fixture
def mock_tools():
    def tool_fn():
        pass

    return [tool_fn]


@pytest.fixture
def mock_subagents():
    def subagent_fn():
        pass

    return [subagent_fn]


@pytest.fixture
def manager(mock_tools, mock_subagents):
    return ChatAgentManager(
        thread_id=123,
        user_id="user42",
        max_tokens=100,
        tools=mock_tools,
        subagents=mock_subagents,
        llm_model="fake-model",
        llm_provider="fake",
    )


def test_init_defaults():
    manager = ChatAgentManager(
        thread_id=1, user_id="u", llm_model="fake-model", llm_provider="fake"
    )
    assert manager.thread_id == 1
    assert manager.user_id == "u"
    assert manager.max_tokens == 2048
    assert manager.tools == []
    assert manager.subagents == []
    assert manager.agent is None
    assert manager.memory is None


@pytest.fixture
def orchestration_tools():
    """Sample tools for orchestration testing."""

    def calendar_tool():
        """Get calendar information."""
        return "Calendar: Meeting at 3pm"

    def email_tool():
        """Send emails."""
        return "Email sent successfully"

    def weather_tool():
        """Get weather information."""
        return "Weather: Sunny, 72°F"

    return [calendar_tool, email_tool, weather_tool]


@pytest.fixture
def sample_subagents():
    """Sample subagent configurations."""
    return [
        {"name": "email_specialist", "tools": ["email_tool"]},
        {"name": "calendar_specialist", "tools": ["calendar_tool"]},
    ]


@pytest.mark.asyncio
async def test_orchestration_initialization(orchestration_tools, sample_subagents):
    """Test that the orchestration layer initializes correctly."""
    manager = ChatAgentManager(
        thread_id=100,
        user_id="orchestration_user",
        tools=orchestration_tools,
        subagents=sample_subagents,
        max_tokens=4096,
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Check basic properties
    assert manager.thread_id == 100
    assert manager.user_id == "orchestration_user"
    assert manager.max_tokens == 4096

    # Check tool distribution
    assert len(manager.tools) == 3
    assert len(manager.subagents) == 2

    # Check tool distribution strategy
    assert "main_agent" in manager.tool_distribution
    assert "specialized_agents" in manager.tool_distribution
    assert (
        len(manager.tool_distribution["main_agent"]) == 3
    )  # All tools go to main for now

    # Check initial state
    assert len(manager.active_agents) == 0
    assert manager.main_agent is None


@pytest.mark.asyncio
@patch("services.chat.chat_agent.history_manager")
async def test_main_agent_creation(mock_history, orchestration_tools):
    """Test that the main agent is created correctly."""
    mock_history.get_thread_history.return_value = []

    manager = ChatAgentManager(
        thread_id=101,
        user_id="main_agent_user",
        tools=orchestration_tools,
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Create main agent
    main_agent = await manager._create_main_agent()

    # Verify agent was created and registered
    assert main_agent is not None
    assert manager.main_agent is main_agent
    assert "main" in manager.active_agents
    assert manager.active_agents["main"] is main_agent

    # Verify agent has the tools
    assert len(main_agent.tools) == 3


@pytest.mark.asyncio
@patch("services.chat.chat_agent.history_manager")
async def test_subagent_creation(mock_history, orchestration_tools, sample_subagents):
    """Test that sub-agents are created correctly."""
    mock_history.get_thread_history.return_value = []

    manager = ChatAgentManager(
        thread_id=102,
        user_id="subagent_user",
        tools=orchestration_tools,
        subagents=sample_subagents,
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Create sub-agents
    subagents = await manager._create_subagents()

    # Verify sub-agents were created
    assert len(subagents) == 2
    assert "subagent_0" in subagents
    assert "subagent_1" in subagents

    # Verify they're registered in active_agents
    assert "subagent_0" in manager.active_agents
    assert "subagent_1" in manager.active_agents

    # Verify sub-agents have different memory configuration
    subagent_0 = subagents["subagent_0"]
    assert not subagent_0.enable_fact_extraction  # Sub-agents don't extract facts
    assert subagent_0.enable_vector_memory  # But they can search history


@pytest.mark.asyncio
@patch("services.chat.chat_agent.history_manager")
async def test_orchestration_build_agent(
    mock_history, orchestration_tools, sample_subagents
):
    """Test building the full orchestrated system."""
    mock_history.get_thread_history.return_value = []

    manager = ChatAgentManager(
        thread_id=103,
        user_id="build_user",
        tools=orchestration_tools,
        subagents=sample_subagents,
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Build the system
    await manager.build_agent()

    # Verify main agent was created
    assert manager.main_agent is not None
    assert "main" in manager.active_agents

    # Verify sub-agents were created
    assert len(manager.active_agents) == 3  # main + 2 subagents
    assert "subagent_0" in manager.active_agents
    assert "subagent_1" in manager.active_agents


@pytest.mark.asyncio
async def test_query_routing():
    """Test query routing logic."""
    manager = ChatAgentManager(
        thread_id=104,
        user_id="routing_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Test routing (currently always returns "main")
    target = await manager._route_query("What's the weather?")
    assert target == "main"

    target = await manager._route_query("Send an email")
    assert target == "main"


@pytest.mark.asyncio
async def test_memory_aggregation():
    """Test memory information aggregation from multiple agents."""
    manager = ChatAgentManager(
        thread_id=105,
        user_id="memory_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Mock the main agent
    mock_agent = AsyncMock()
    mock_agent.get_memory_info.return_value = {"blocks": 3, "tokens": 1500}
    manager.main_agent = mock_agent
    manager.active_agents["main"] = mock_agent

    # Mock a sub-agent
    mock_subagent = AsyncMock()
    mock_subagent.get_memory_info.return_value = {"blocks": 2, "tokens": 800}
    manager.active_agents["subagent_0"] = mock_subagent

    # Get aggregated memory
    memory_info = await manager.get_memory()

    # Verify aggregation
    assert len(memory_info) == 2
    assert memory_info[0]["agent"] == "main"
    assert memory_info[0]["memory"]["blocks"] == 3
    assert memory_info[1]["agent"] == "subagent_0"
    assert memory_info[1]["memory"]["blocks"] == 2


@pytest.mark.asyncio
@patch("services.chat.chat_agent.history_manager")
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_end_to_end_orchestration(mock_history, orchestration_tools):
    """Test end-to-end orchestration flow."""
    # Properly mock all the async methods
    mock_history.get_thread_history = AsyncMock(return_value=[])
    mock_history.get_thread = AsyncMock(return_value=MagicMock(id=106))
    mock_history.create_thread = AsyncMock(return_value=MagicMock(id=106))
    mock_history.append_message = AsyncMock(return_value=None)

    manager = ChatAgentManager(
        thread_id=106,
        user_id="e2e_user",
        tools=orchestration_tools,
        llm_model="fake-model",
        llm_provider="fake",
    )

    # This should build the system and process the query
    response = await manager.chat("Hello, orchestrate this!")

    # With FakeLLM in test environment, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert "Hello, orchestrate this!" in response
    assert manager.main_agent is not None
