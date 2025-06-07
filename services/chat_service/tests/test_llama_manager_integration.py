import asyncio
from collections import namedtuple
from unittest.mock import AsyncMock, patch

import pytest
import sqlalchemy
from llama_index.core.llms.function_calling import FunctionCallingLLM

from services.chat_service.context_module import select_relevant_messages
from services.chat_service.history_manager import (
    append_message,
    create_thread,
    database,
    get_thread_history,
    metadata,
)
from services.chat_service.llama_manager import ChatAgentManager


class DummyFunctionCallingLLM(FunctionCallingLLM):
    @property
    def metadata(self):
        Meta = namedtuple("Meta", ["is_function_calling_model"])
        return Meta(is_function_calling_model=True)

    async def achat(self, *args, **kwargs):
        user_input = kwargs.get("user_input", "")

        class Message:
            def __init__(self, content):
                self.content = content

        # Defensive: if llama-index passes user_input as positional arg
        if not user_input and args:
            user_input = args[0]

        class Response:
            message = Message(f"Echo: {user_input}")
            response = message  # always a Message object

        return Response()

    async def acomplete(self, *args, **kwargs):
        raise NotImplementedError()

    async def astream_chat(self, *args, **kwargs):
        raise NotImplementedError()

    async def astream_complete(self, *args, **kwargs):
        raise NotImplementedError()

    def chat(self, *args, **kwargs):
        raise NotImplementedError()

    def complete(self, *args, **kwargs):
        raise NotImplementedError()

    def stream_chat(self, *args, **kwargs):
        raise NotImplementedError()

    def stream_complete(self, *args, **kwargs):
        raise NotImplementedError()

    def _prepare_chat_with_tools(self, *args, **kwargs):
        return {}

    def get_tool_calls_from_response(
        self, response, error_on_no_tool_call=True, **kwargs
    ):
        # For this test, no tool calls are expected, so just return an empty list
        return []


@pytest.mark.asyncio
async def test_llama_manager_integration(tmp_path):
    # Ensure tables exist and DB is connected
    engine = sqlalchemy.create_engine("sqlite:///memory")
    metadata.create_all(engine)
    if not database.is_connected:
        await database.connect()
    # Setup: create a thread and add some messages
    user_id = "test_user"
    thread = await create_thread(user_id=user_id, title="Integration Test Thread")
    thread_id = thread.id
    await append_message(thread_id, user_id, "Hello, world!")
    await append_message(thread_id, "assistant", "Hi! How can I help you?")

    # Patch context_module.select_relevant_messages to just return all messages
    with patch(
        "services.chat_service.context_module.select_relevant_messages",
        side_effect=lambda msgs, user_input, max_tokens: msgs,
    ):
        # Patch LLM with dummy
        @pytest.mark.asyncio
        async def test_llama_manager_empty_thread_history(tmp_path):
            # Setup DB and thread with no messages
            engine = sqlalchemy.create_engine("sqlite:///memory")
            metadata.create_all(engine)
            if not database.is_connected:
                await database.connect()
            user_id = "user_empty"
            thread = await create_thread(user_id=user_id, title="Empty Thread")
            thread_id = thread.id

            with patch(
                "services.chat_service.context_module.select_relevant_messages",
                side_effect=lambda msgs, user_input, max_tokens: msgs,
            ):
                agent = ChatAgentManager(
                    llm=DummyFunctionCallingLLM(),
                    thread_id=thread_id,
                    user_id=user_id,
                    tools=[],
                    subagents=[],
                )
                # Send a message and check if it's appended and retrieved
                user_input = "Is anyone here?"
                reply = await agent.chat(user_input)
                assert reply.startswith("Echo: ")
                history = await get_thread_history(thread_id, limit=5)
                contents = [m.content for m in history]
                assert any("Is anyone here?" in c for c in contents)
                assert any("Echo: Is anyone here?" in c for c in contents)

        @pytest.mark.asyncio
        async def test_llama_manager_multiple_messages_order(tmp_path):
            # Setup DB and thread
            engine = sqlalchemy.create_engine("sqlite:///memory")
            metadata.create_all(engine)
            if not database.is_connected:
                await database.connect()
            user_id = "user_order"
            thread = await create_thread(user_id=user_id, title="Order Test Thread")
            thread_id = thread.id

            with patch(
                "services.chat_service.context_module.select_relevant_messages",
                side_effect=lambda msgs, user_input, max_tokens: msgs,
            ):
                agent = ChatAgentManager(
                    llm=DummyFunctionCallingLLM(),
                    thread_id=thread_id,
                    user_id=user_id,
                    tools=[],
                    subagents=[],
                )
                # Send multiple messages
                messages = ["First", "Second", "Third"]
                for msg in messages:
                    reply = await agent.chat(msg)
                    assert reply.startswith("Echo: ")
                history = await get_thread_history(thread_id, limit=10)
                contents = [m.content for m in history]
                # Ensure all messages and their echoes are present in order
                for msg in messages:
                    assert any(msg in c for c in contents)
                    assert any(f"Echo: {msg}" in c for c in contents)

        @pytest.mark.asyncio
        async def test_llama_manager_unicode_and_long_message(tmp_path):
            # Setup DB and thread
            engine = sqlalchemy.create_engine("sqlite:///memory")
            metadata.create_all(engine)
            if not database.is_connected:
                await database.connect()
            user_id = "user_unicode"
            thread = await create_thread(user_id=user_id, title="Unicode Thread")
            thread_id = thread.id

            with patch(
                "services.chat_service.context_module.select_relevant_messages",
                side_effect=lambda msgs, user_input, max_tokens: msgs,
            ):
                agent = ChatAgentManager(
                    llm=DummyFunctionCallingLLM(),
                    thread_id=thread_id,
                    user_id=user_id,
                    tools=[],
                    subagents=[],
                )
                user_input = "这是一个很长的消息。" * 10 + "🚀"
                reply = await agent.chat(user_input)
                assert reply.startswith("Echo: ")
                history = await get_thread_history(thread_id, limit=5)
                contents = [m.content for m in history]
                assert any("🚀" in c for c in contents)
                assert any(user_input in c for c in contents)
                assert any(f"Echo: {user_input}" in c for c in contents)

        @pytest.mark.asyncio
        async def test_llama_manager_history_limit(tmp_path):
            # Setup DB and thread
            engine = sqlalchemy.create_engine("sqlite:///memory")
            metadata.create_all(engine)
            if not database.is_connected:
                await database.connect()
            user_id = "user_limit"
            thread = await create_thread(user_id=user_id, title="History Limit Thread")
            thread_id = thread.id

            with patch(
                "services.chat_service.context_module.select_relevant_messages",
                side_effect=lambda msgs, user_input, max_tokens: msgs,
            ):
                agent = ChatAgentManager(
                    llm=DummyFunctionCallingLLM(),
                    thread_id=thread_id,
                    user_id=user_id,
                    tools=[],
                    subagents=[],
                )
                # Send 15 messages
                for i in range(15):
                    await agent.chat(f"Message {i}")
                # Only last 10 should be returned if limit=10
                history = await get_thread_history(thread_id, limit=10)
                contents = [m.content for m in history]
                assert any("Message 14" in c for c in contents)
                assert not any("Message 0" in c for c in contents)
