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
def manager(mock_llm, mock_tools, mock_subagents):
    return ChatAgentManager(
        llm=mock_llm,
        thread_id=123,
        user_id="user42",
        max_tokens=100,
        tools=mock_tools,
        subagents=mock_subagents,
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
    mock_context.select_relevant_messages.return_value = [
        {"user_id": "user42", "content": "hi"}
    ]

    # Run
    result = await manager.get_memory("hi")

    # Assert
    mock_history.get_thread_history.assert_awaited_with(123, limit=100)
    mock_context.select_relevant_messages.assert_called_once()
    assert result == [{"user_id": "user42", "content": "hi"}]


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.FunctionTool")
@patch("services.chat_service.llama_manager.ChatMemoryBuffer")
@patch("services.chat_service.llama_manager.FunctionCallingAgent")
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
async def test_build_agent_constructs_agent(
    mock_context,
    mock_history,
    mock_agent,
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
    mock_history.get_thread_history = AsyncMock(return_value=[])
    mock_context.select_relevant_messages.return_value = fake_messages
    mock_tool.from_defaults.side_effect = lambda fn: f"tool-{fn.__name__}"
    mock_memory.from_defaults.return_value = "memory"
    mock_agent.from_tools.return_value = "agent"

    # Run
    await manager.build_agent("hi")

    # Assert
    assert manager.memory == "memory"
    assert manager.agent == "agent"
    # Should wrap all tools and subagents
    assert mock_tool.from_defaults.call_count == len(mock_tools) + len(mock_subagents)
    mock_agent.from_tools.assert_called_once()
    mock_memory.from_defaults.assert_called_once()
    # Check chat_history construction
    args, kwargs = mock_memory.from_defaults.call_args
    chat_history = kwargs.get("chat_history") or args[0]
    assert chat_history[0].role == "user"
    assert chat_history[0].content == "hi"
    assert chat_history[1].role == "assistant"
    assert chat_history[1].content == "hello"


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.FunctionTool")
@patch("services.chat_service.llama_manager.ChatMemoryBuffer")
@patch("services.chat_service.llama_manager.FunctionCallingAgent")
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
async def test_chat_calls_agent_and_appends_history(
    mock_context, mock_history, mock_agent, mock_memory, mock_tool, manager
):
    # Setup mock thread
    mock_thread = MagicMock()
    mock_thread.id = 123
    mock_history.Thread.objects.get = AsyncMock(return_value=mock_thread)

    # Patch async methods with AsyncMock
    mock_history.append_message = AsyncMock()
    mock_history.get_thread_history = AsyncMock(return_value=[])
    mock_history.create_thread = AsyncMock(return_value=mock_thread)

    # Setup agent
    fake_agent = MagicMock()
    fake_response = MagicMock(response="agent reply")
    fake_agent.achat = AsyncMock(return_value=fake_response)
    manager.agent = fake_agent
    manager.user_id = "user42"
    manager.thread_id = 123

    # Run
    result = await manager.chat("hello world")

    # Assert
    fake_agent.achat.assert_awaited_with("hello world")
    mock_history.append_message.assert_any_await(123, "user42", "hello world")
    mock_history.append_message.assert_any_await(123, "assistant", "agent reply")
    assert result == "agent reply"


@pytest.mark.asyncio
@patch("services.chat_service.llama_manager.FunctionTool")
@patch("services.chat_service.llama_manager.ChatMemoryBuffer")
@patch("services.chat_service.llama_manager.FunctionCallingAgent")
@patch("services.chat_service.llama_manager.history_manager")
@patch("services.chat_service.llama_manager.context_module")
async def test_chat_builds_agent_if_none(
    mock_context, mock_history, mock_agent, mock_memory, mock_tool, manager
):
    # Setup mock thread
    mock_thread = MagicMock()
    mock_thread.id = 123
    mock_history.Thread.objects.get = AsyncMock(return_value=mock_thread)
    mock_history.create_thread = AsyncMock(return_value=mock_thread)

    # Setup agent
    fake_agent = MagicMock()
    fake_agent.achat = AsyncMock(return_value=MagicMock(response="foo"))
    mock_agent.from_tools.return_value = fake_agent

    # Setup other mocks
    mock_history.append_message = AsyncMock()
    mock_history.get_thread_history = AsyncMock(return_value=[])
    mock_context.select_relevant_messages.return_value = []
    mock_tool.from_defaults.side_effect = lambda fn: f"tool-{fn.__name__}"
    mock_memory.from_defaults.return_value = "memory"

    # Clear any existing agent
    manager.agent = None

    # Run
    result = await manager.chat("test input")

    # Assert
    assert result == "foo"
    assert manager.agent is not None
    mock_history.append_message.assert_any_await(123, manager.user_id, "test input")
    mock_history.append_message.assert_any_await(123, "assistant", "foo")


def test_init_defaults():
    manager = ChatAgentManager(llm="llm", thread_id=1, user_id="u")
    assert manager.llm == "llm"
    assert manager.thread_id == 1
    assert manager.user_id == "u"
    assert manager.max_tokens == 2048
    assert manager.tools == []
    assert manager.subagents == []
    assert manager.agent is None
    assert manager.memory is None
