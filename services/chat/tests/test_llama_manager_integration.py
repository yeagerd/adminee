"""
Integration tests for ChatAgentManager orchestration layer.

This test suite covers:
- Basic chat functionality through the orchestration layer
- Thread history management
- Message ordering and persistence
- Unicode and long message handling
- Tool and subagent orchestration
- Memory block coordination
"""

# Set required environment variables before any imports
import os

os.environ.setdefault("DB_URL_CHAT", "sqlite:///test.db")


import logging
import os
import tempfile
from unittest.mock import patch

import pytest
import pytest_asyncio

from services.chat import history_manager
from services.chat.llama_manager import ChatAgentManager

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Set up test database with proper tables for all tests."""
    # Create a temporary database file for testing
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Set the database URL for testing
    original_db_url = os.environ.get("DB_URL_CHAT")
    os.environ["DB_URL_CHAT"] = f"sqlite:///{db_path}"

    try:
        # Initialize database tables
        await history_manager.init_db()
        yield
    finally:
        # Cleanup
        if original_db_url:
            os.environ["DB_URL_CHAT"] = original_db_url
        elif "DB_URL_CHAT" in os.environ:
            del os.environ["DB_URL_CHAT"]

        # Remove temporary database file
        try:
            os.unlink(db_path)
        except OSError:
            pass


class DummyTool:
    """Sample tool for testing."""

    def __call__(self):
        return "dummy tool result"

    def __name__(self):
        return "dummy_tool"


@pytest.mark.asyncio
async def test_manager_initialization():
    """Test ChatAgentManager initialization with orchestration parameters."""
    manager = ChatAgentManager(
        thread_id=1,
        user_id="test_user",
        max_tokens=2048,
        tools=[DummyTool()],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    assert manager.thread_id == 1
    assert manager.user_id == "test_user"
    assert manager.max_tokens == 2048
    assert len(manager.tools) == 1
    assert manager.main_agent is None  # Not built yet
    assert len(manager.active_agents) == 0


@pytest.mark.asyncio
async def test_manager_build_agent():
    """Test building the orchestrated agent system."""
    # Create a thread first
    thread = await history_manager.create_thread("test_user", "Test Thread")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="test_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Build agent system
    await manager.build_agent("test input")

    # Main agent should be created
    assert manager.main_agent is not None
    assert "main" in manager.active_agents
    assert manager.agent == manager.main_agent

    # Properties should work
    assert manager.llm is not None
    assert manager.memory is not None


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_basic_chat():
    """Test basic chat functionality through orchestration layer."""
    # Create a thread
    thread = await history_manager.create_thread("chat_user", "Chat Test")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="chat_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Send a message
    user_input = "Hello, orchestrated world!"
    response = await manager.chat(user_input)

    # Should get a response
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert user_input in response

    # Check that messages were stored in database
    messages = await history_manager.get_thread_history(thread.id, limit=10)
    contents = [msg.content for msg in messages]

    # Should have both user message and assistant response
    assert any(user_input in content for content in contents)
    assert any(len(content) > 0 for content in contents if content != user_input)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_empty_thread():
    """Test manager with a newly created empty thread."""
    # Create empty thread
    thread = await history_manager.create_thread("empty_user", "Empty Thread")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="empty_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    user_input = "Is anyone here?"
    response = await manager.chat(user_input)

    assert response is not None
    assert len(response) > 0

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert user_input in response

    # Verify message history
    history = await history_manager.get_thread_history(thread.id, limit=5)
    contents = [msg.content for msg in history]

    assert any(user_input in content for content in contents)
    assert len(history) >= 1  # At least the user message should be there


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_multiple_messages_order():
    """Test message ordering with multiple sequential messages."""
    thread = await history_manager.create_thread("order_user", "Order Test Thread")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="order_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Send multiple messages in sequence
    messages = ["First message", "Second message", "Third message"]
    responses = []

    for msg in messages:
        response = await manager.chat(msg)
        responses.append(response)
        assert response is not None
        assert len(response) > 0

        # With FakeLLM, expect the fake response format
        assert "[FAKE LLM RESPONSE]" in response
        assert msg in response

    # Check message history
    history = await history_manager.get_thread_history(thread.id, limit=20)
    contents = [msg.content for msg in history]

    # All user messages should be present
    for msg in messages:
        assert any(msg in content for content in contents)

    # Should have multiple messages (user + assistant responses)
    assert len(history) >= len(messages)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_unicode_and_long_message():
    """Test handling of unicode characters and long messages."""
    thread = await history_manager.create_thread("unicode_user", "Unicode Thread")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="unicode_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Test with unicode and long content
    user_input = "这是一个很长的消息。" * 10 + "🚀🌟✨"
    response = await manager.chat(user_input)

    assert response is not None
    assert len(response) > 0

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    # Note: FakeLLM might truncate very long inputs, so just check for emoji
    assert "🚀" in response

    # Check database storage
    history = await history_manager.get_thread_history(thread.id, limit=5)
    contents = [msg.content for msg in history]

    # Unicode characters should be preserved
    assert any("🚀" in content for content in contents)
    assert any("这是一个很长的消息" in content for content in contents)
    assert any(user_input in content for content in contents)


@pytest.mark.asyncio
async def test_manager_memory_access():
    """Test accessing memory information through orchestration layer."""
    thread = await history_manager.create_thread("memory_user", "Memory Test")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="memory_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Build agent first
    await manager.build_agent()

    # Get memory info
    memory_info = await manager.get_memory("test input")

    assert memory_info is not None
    assert isinstance(memory_info, list)
    assert len(memory_info) >= 1  # Should have at least main agent memory

    # Main agent memory should be present
    main_memory = next((info for info in memory_info if info["agent"] == "main"), None)
    assert main_memory is not None
    assert "memory" in main_memory


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_with_tools():
    """Test manager with tools in orchestration setup."""
    thread = await history_manager.create_thread("tool_user", "Tool Test")

    def sample_tool():
        """A sample tool for testing."""
        return "tool executed"

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="tool_user",
        tools=[sample_tool],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Should initialize with tools
    assert len(manager.tools) == 1
    assert manager.tool_distribution["main_agent"] == [sample_tool]

    # Build and test
    await manager.build_agent()
    response = await manager.chat("Hello with tools")

    assert response is not None
    assert manager.main_agent is not None

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert "Hello with tools" in response


@pytest.mark.asyncio
async def test_manager_tool_distribution():
    """Test tool distribution analysis in orchestration layer."""

    def tool1():
        return "tool1"

    def tool2():
        return "tool2"

    manager = ChatAgentManager(
        thread_id=999,  # Dummy thread_id for this test
        user_id="dist_user",
        tools=[tool1, tool2],
        subagents=[{"name": "specialist"}],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Check tool distribution
    distribution = manager.tool_distribution
    assert "main_agent" in distribution
    assert "specialized_agents" in distribution

    # Currently all tools go to main agent
    assert len(distribution["main_agent"]) == 2
    assert tool1 in distribution["main_agent"]
    assert tool2 in distribution["main_agent"]


@pytest.mark.asyncio
async def test_manager_with_subagents():
    """Test manager initialization with subagent configurations."""
    thread = await history_manager.create_thread("sub_user", "Subagent Test")

    subagent_configs = [
        {"name": "email_agent", "specialty": "email"},
        {"name": "calendar_agent", "specialty": "calendar"},
    ]

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="sub_user",
        tools=[],
        subagents=subagent_configs,
        llm_model="fake-model",
        llm_provider="fake",
    )

    assert len(manager.subagents) == 2

    # Build agent system (should create subagents)
    await manager.build_agent()

    # Should have main agent plus subagents
    assert len(manager.active_agents) >= 1  # At least main agent
    assert "main" in manager.active_agents


@pytest.mark.asyncio
async def test_manager_query_routing():
    """Test query routing logic in orchestration layer."""
    thread = await history_manager.create_thread("route_user", "Routing Test")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="route_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Test routing decision
    route = await manager._route_query("Hello world")

    # Currently always routes to main
    assert route == "main"


@pytest.mark.asyncio
async def test_manager_property_access():
    """Test property access patterns for backward compatibility."""
    thread = await history_manager.create_thread("prop_user", "Property Test")

    manager = ChatAgentManager(
        thread_id=thread.id,
        user_id="prop_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Before building - properties should handle None gracefully
    assert manager.llm is None
    assert manager.memory is None

    # Build agent
    await manager.build_agent()

    # After building - properties should work
    assert manager.llm is not None
    assert manager.agent is not None
    assert manager.memory is not None

    # Test setter
    original_agent = manager.agent
    manager.agent = original_agent  # Should work without error
    assert manager.agent == original_agent


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_error_handling():
    """Test error handling in orchestration scenarios."""
    manager = ChatAgentManager(
        thread_id=99999,  # Non-existent thread
        user_id="error_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Should handle non-existent thread gracefully
    response = await manager.chat("Test message")

    # Should still get a response (thread gets created)
    assert response is not None

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert "Test message" in response


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": ""})  # Force FakeLLM by removing API key
async def test_manager_thread_auto_creation():
    """Test automatic thread creation when thread doesn't exist."""
    non_existent_thread_id = 99999

    manager = ChatAgentManager(
        thread_id=non_existent_thread_id,
        user_id="auto_user",
        tools=[],
        subagents=[],
        llm_model="fake-model",
        llm_provider="fake",
    )

    # This should work by creating a new thread
    response = await manager.chat("Auto-create thread test")

    assert response is not None
    assert isinstance(response, str)

    # With FakeLLM, expect the fake response format
    assert "[FAKE LLM RESPONSE]" in response
    assert "Auto-create thread test" in response

    # The manager should now have a valid main agent
    assert manager.main_agent is not None
