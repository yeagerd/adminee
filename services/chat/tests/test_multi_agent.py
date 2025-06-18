"""
Tests for the multi-agent workflow system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat.agents.calendar_agent import CalendarAgent
from services.chat.agents.coordinator_agent import CoordinatorAgent
from services.chat.agents.document_agent import DocumentAgent
from services.chat.agents.draft_agent import DraftAgent
from services.chat.agents.email_agent import EmailAgent
from services.chat.agents.workflow_agent import WorkflowAgent


@pytest.fixture
def mock_history_manager():
    """Mock the history manager."""
    with patch("services.chat.agents.workflow_agent.history_manager") as mock:
        mock.append_message = AsyncMock()
        mock.get_thread_history = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def multi_agent_workflow(mock_history_manager):
    """Create a WorkflowAgent instance with multi-agent mode enabled."""
    return WorkflowAgent(
        thread_id=123,
        user_id="test_user",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=1000,
        use_multi_agent=True,
    )


@pytest.fixture
def single_agent_workflow(mock_history_manager):
    """Create a WorkflowAgent instance with single-agent mode."""
    return WorkflowAgent(
        thread_id=124,
        user_id="test_user",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=1000,
        use_multi_agent=False,
    )


def test_multi_agent_initialization(multi_agent_workflow):
    """Test that multi-agent mode initializes correctly."""
    assert multi_agent_workflow.use_multi_agent is True
    assert multi_agent_workflow.specialized_agents == {}  # Empty until built
    assert multi_agent_workflow.thread_id == 123
    assert multi_agent_workflow.user_id == "test_user"


def test_single_agent_initialization(single_agent_workflow):
    """Test that single-agent mode initializes correctly."""
    assert single_agent_workflow.use_multi_agent is False
    assert single_agent_workflow.specialized_agents == {}
    assert single_agent_workflow.function_agent is None  # Not built yet


@pytest.mark.asyncio
async def test_multi_agent_build(multi_agent_workflow, mock_history_manager):
    """Test building multi-agent workflow."""
    # Mock the ChatAgent build_agent method
    multi_agent_workflow.chat_agent.build_agent = AsyncMock()
    multi_agent_workflow.chat_agent._load_chat_history_from_db = AsyncMock(
        return_value=[]
    )

    await multi_agent_workflow.build_agent("test input")

    # Check that specialized agents were created
    assert len(multi_agent_workflow.specialized_agents) == 5
    expected_agents = [
        "Coordinator",
        "CalendarAgent",
        "EmailAgent",
        "DocumentAgent",
        "DraftAgent",
    ]
    for agent_name in expected_agents:
        assert agent_name in multi_agent_workflow.specialized_agents

    # Check that workflow and context are initialized
    assert multi_agent_workflow.agent_workflow is not None
    assert multi_agent_workflow.context is not None

    # Check that ChatAgent was built
    multi_agent_workflow.chat_agent.build_agent.assert_called_once_with("test input")


@pytest.mark.asyncio
async def test_single_agent_build(single_agent_workflow, mock_history_manager):
    """Test building single-agent workflow."""
    # Mock the ChatAgent build_agent method
    single_agent_workflow.chat_agent.build_agent = AsyncMock()
    single_agent_workflow.chat_agent._load_chat_history_from_db = AsyncMock(
        return_value=[]
    )

    await single_agent_workflow.build_agent("test input")

    # Check that single function agent was created
    assert single_agent_workflow.function_agent is not None
    assert len(single_agent_workflow.specialized_agents) == 0  # No specialized agents

    # Check that workflow and context are initialized
    assert single_agent_workflow.agent_workflow is not None
    assert single_agent_workflow.context is not None


def test_coordinator_agent_creation():
    """Test that CoordinatorAgent can be created."""
    agent = CoordinatorAgent(
        llm_model="fake-model",
        llm_provider="fake",
    )

    assert agent.name == "Coordinator"
    assert "coordinator" in agent.description.lower()
    assert len(agent.tools) > 0  # Should have coordination tools


def test_calendar_agent_creation():
    """Test that CalendarAgent can be created."""
    agent = CalendarAgent(
        llm_model="fake-model",
        llm_provider="fake",
        office_service_url="http://localhost:8001",
    )

    assert agent.name == "CalendarAgent"
    assert "calendar" in agent.description.lower()
    assert len(agent.tools) > 0  # Should have calendar tools


def test_email_agent_creation():
    """Test that EmailAgent can be created."""
    agent = EmailAgent(
        llm_model="fake-model",
        llm_provider="fake",
        office_service_url="http://localhost:8001",
    )

    assert agent.name == "EmailAgent"
    assert "email" in agent.description.lower()
    assert len(agent.tools) > 0  # Should have email tools


def test_document_agent_creation():
    """Test that DocumentAgent can be created."""
    agent = DocumentAgent(
        llm_model="fake-model",
        llm_provider="fake",
        office_service_url="http://localhost:8001",
    )

    assert agent.name == "DocumentAgent"
    assert "document" in agent.description.lower()
    assert len(agent.tools) > 0  # Should have document tools


def test_draft_agent_creation():
    """Test that DraftAgent can be created."""
    agent = DraftAgent(
        llm_model="fake-model",
        llm_provider="fake",
    )

    assert agent.name == "DraftAgent"
    assert "draft" in agent.description.lower()
    assert len(agent.tools) > 0  # Should have drafting tools


@pytest.mark.asyncio
async def test_multi_agent_chat_flow(multi_agent_workflow, mock_history_manager):
    """Test multi-agent chat functionality."""
    # Mock the agent workflow
    mock_response = "Multi-agent response"

    with patch.object(
        multi_agent_workflow, "build_agent", new_callable=AsyncMock
    ) as mock_build:
        # Create mock workflow and context
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value=mock_response)
        multi_agent_workflow.agent_workflow = mock_workflow

        mock_context = MagicMock()
        multi_agent_workflow.context = mock_context

        # Mock chat agent memory
        multi_agent_workflow.chat_agent.memory = AsyncMock()
        multi_agent_workflow.chat_agent.memory.put_messages = AsyncMock()

        # Test chat
        response = await multi_agent_workflow.chat("Hello")

        assert response == mock_response

        # Verify database calls
        assert mock_history_manager.append_message.call_count == 2


def test_agent_handoff_capabilities():
    """Test that agents have proper handoff capabilities."""
    # Create all agents
    coordinator = CoordinatorAgent(llm_model="fake-model", llm_provider="fake")
    calendar_agent = CalendarAgent(llm_model="fake-model", llm_provider="fake")
    email_agent = EmailAgent(llm_model="fake-model", llm_provider="fake")
    document_agent = DocumentAgent(llm_model="fake-model", llm_provider="fake")
    draft_agent = DraftAgent(llm_model="fake-model", llm_provider="fake")

    # Check handoff configurations
    assert "CalendarAgent" in coordinator.can_handoff_to
    assert "EmailAgent" in coordinator.can_handoff_to
    assert "DocumentAgent" in coordinator.can_handoff_to
    assert "DraftAgent" in coordinator.can_handoff_to

    assert "DraftAgent" in calendar_agent.can_handoff_to
    assert "DraftAgent" in email_agent.can_handoff_to
    assert "DraftAgent" in document_agent.can_handoff_to


def test_default_system_prompts():
    """Test that system prompts are different for single vs multi-agent mode."""
    single_agent = WorkflowAgent(
        thread_id=1,
        user_id="test",
        llm_model="fake-model",
        llm_provider="fake",
        use_multi_agent=False,
    )

    multi_agent = WorkflowAgent(
        thread_id=2,
        user_id="test",
        llm_model="fake-model",
        llm_provider="fake",
        use_multi_agent=True,
    )

    single_prompt = single_agent._get_default_system_prompt()
    multi_prompt = multi_agent._get_default_system_prompt()

    assert single_prompt != multi_prompt
    assert "coordinator" in multi_prompt.lower()
    assert "tools" in single_prompt.lower()


@pytest.mark.asyncio
async def test_context_state_initialization(multi_agent_workflow, mock_history_manager):
    """Test that multi-agent context has proper initial state."""
    # Mock the ChatAgent build_agent method
    multi_agent_workflow.chat_agent.build_agent = AsyncMock()
    multi_agent_workflow.chat_agent._load_chat_history_from_db = AsyncMock(
        return_value=[]
    )

    await multi_agent_workflow.build_agent("test input")

    # The initial state should include keys for each agent type
    initial_state = multi_agent_workflow.agent_workflow.initial_state

    assert "thread_id" in initial_state
    assert "user_id" in initial_state
    assert "calendar_info" in initial_state
    assert "email_info" in initial_state
    assert "document_info" in initial_state
    assert "draft_info" in initial_state
    assert initial_state["thread_id"] == str(multi_agent_workflow.thread_id)
    assert initial_state["user_id"] == multi_agent_workflow.user_id
