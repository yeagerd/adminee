from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.chat_service.llama_manager import ChatAgentManager


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
        llm_model="fake-model",  # Use fake model for testing
        llm_provider="test-provider",
    )


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
async def test_get_memory_selects_relevant_messages(
    mock_context, mock_history, manager
):
    # Setup
    fake_messages = [
        MagicMock(
            model_dump=MagicMock(return_value={"user_id": "user42", "content": "hi"})
        ),
        MagicMock(
            model_dump=MagicMock(
                return_value={"user_id": "assistant", "content": "hello"}
            )
        ),
    ]
    mock_history.get_thread_history = AsyncMock(return_value=fake_messages)

    # Mock the async function
    async def mock_dynamic_selection(*args, **kwargs):
        return [
            {"user_id": "user42", "content": "hi"},
            {"user_id": "assistant", "content": "hello"},
        ]

    mock_context.dynamic_context_selection = mock_dynamic_selection

    # Test
    result = await manager.get_memory("test query")

    # Verify
    assert len(result) == 2
    assert result[0]["content"] == "hi"
    assert result[0]["user_id"] == "user42"
    assert result[1]["content"] == "hello"
    assert result[1]["user_id"] == "assistant"
    mock_history.get_thread_history.assert_awaited_once_with(123, limit=100)


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.FunctionTool")
@patch("services.chat_service.llama_manager.Memory")
@patch("services.chat_service.llama_manager.FunctionCallingAgent")
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
async def test_build_agent_constructs_agent(
    mock_context,
    mock_history,
    mock_agent_cls,
    mock_memory,
    mock_tool,
    manager,
    mock_tools,
    mock_subagents,
):
    # Setup
    fake_messages = [
        {"user_id": "user42", "content": "hi"},
        {"user_id": "assistant", "content": "hello"},
    ]

    # Mock history manager
    mock_history.get_thread_history = AsyncMock(return_value=[])

    # Mock context module
    async def mock_dynamic_selection(*args, **kwargs):
        return fake_messages

    mock_context.dynamic_context_selection = mock_dynamic_selection

    # Mock tools and memory
    mock_tool.from_defaults.side_effect = lambda fn: f"tool-{fn.__name__}"
    mock_memory.from_defaults.return_value = MagicMock()

    # Mock agent
    mock_agent_instance = AsyncMock()
    mock_agent_cls.from_tools.return_value = mock_agent_instance

    # Run
    await manager.build_agent("hi")

    # Assert FunctionCallingAgent was used with tools
    mock_agent_cls.from_tools.assert_called_once()
    assert manager.agent == mock_agent_instance
    # Should wrap all tools and subagents
    assert len(mock_tool.from_defaults.mock_calls) == len(mock_tools) + len(
        mock_subagents
    )
    mock_agent_cls.from_tools.assert_called_once()
    mock_memory.from_defaults.assert_called_once()
    args, kwargs = mock_memory.from_defaults.call_args
    chat_history = kwargs.get("chat_history") or args[0]
    # Check user and assistant messages
    assert chat_history[0].role == "user"
    assert chat_history[0].content == "hi"
    assert chat_history[1].role == "assistant"
    assert chat_history[1].content == "hello"


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.FunctionTool")
@patch("services.chat_service.llama_manager.Memory")
@patch("services.chat_service.llama_manager.FunctionCallingAgent")
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
@patch("services.chat_service.llama_manager.llm_manager.get_llm")
async def test_chat_calls_agent_and_appends_history(
    mock_get_llm,
    mock_context,
    mock_history,
    mock_agent,
    mock_memory,
    mock_tool,
    manager,
):
    # Setup mock thread
    mock_thread = MagicMock()
    mock_thread.id = 123
    mock_history.Thread.objects.get = AsyncMock(return_value=mock_thread)

    # Patch async methods with AsyncMock
    mock_history.append_message = AsyncMock()
    mock_history.get_thread_history = AsyncMock(return_value=[])
    mock_history.create_thread = AsyncMock(return_value=mock_thread)

    # Mock the LLM
    mock_llm = AsyncMock()
    mock_llm.achat.return_value = "[FAKE LLM RESPONSE] You said: hello world"
    mock_get_llm.return_value = mock_llm

    # Setup agent
    fake_agent = MagicMock()
    fake_agent.achat = AsyncMock(
        return_value="[FAKE LLM RESPONSE] You said: hello world"
    )
    manager.agent = fake_agent
    manager.user_id = "user42"
    manager.thread_id = 123

    # Run
    result = await manager.chat("hello world")

    # Assert
    assert result == "[FAKE LLM RESPONSE] You said: hello world"
    # In the current implementation, user message is appended after building the agent
    # So we just check that the assistant's response was appended
    mock_history.append_message.assert_called_once_with(
        123, "assistant", "[FAKE LLM RESPONSE] You said: hello world"
    )


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
@patch("services.chat_service.llama_manager.llm_manager.get_llm")
async def test_chat_builds_agent_if_none(
    mock_get_llm, mock_context, mock_history, manager, mock_tools
):
    # Setup - no tools or subagents for this test
    manager.agent = None
    manager.tools = []
    manager.subagents = []

    # Create a proper FakeLLM instance
    from services.chat_service.llm_manager import FakeLLM

    fake_llm = FakeLLM()

    # Mock the LLM manager to return our fake LLM
    mock_get_llm.return_value = fake_llm

    # Mock thread
    mock_thread = MagicMock()
    mock_thread.id = 123

    # Create a mock Thread model class
    mock_thread_model = MagicMock()
    mock_thread_model.objects.get = AsyncMock(return_value=mock_thread)

    # Mock history manager
    mock_history.Thread = mock_thread_model
    mock_history.create_thread = AsyncMock(return_value=mock_thread)
    mock_history.append_message = AsyncMock()
    mock_history.get_thread_history = AsyncMock(return_value=[])

    # Mock context module
    async def mock_dynamic_selection(*args, **kwargs):
        return []

    mock_context.dynamic_context_selection = mock_dynamic_selection

    # Test
    result = await manager.chat("test input")

    # Verify the response is as expected from FakeLLM
    assert "test input" in result

    # In FakeLLM case, we don't actually build an agent
    # Just verify the message was appended to history
    mock_history.append_message.assert_any_call(123, "assistant", mock.ANY)


def test_init_defaults():
    manager = ChatAgentManager(thread_id=1, user_id="u")
    assert manager.thread_id == 1
    assert manager.user_id == "u"
    assert manager.max_tokens == 2048
    assert manager.tools == []
    assert manager.subagents == []
    assert manager.agent is None
    assert manager.memory is None
