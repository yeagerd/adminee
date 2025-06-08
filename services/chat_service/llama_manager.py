# llama_manager.py
"""
Planning agent for chat_service using LiteLLM and llama-index.
Implements agent loop, tool/subagent registration, and token-constrained memory.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from llama_index.core.agent.function_calling.base import FunctionCallingAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.types import BaseTool

from services.chat_service import context_module, history_manager

load_dotenv()

logger = logging.getLogger(__name__)


class FakeLLM:
    """A fake LLM for testing and offline mode."""

    async def achat(self, query):
        logger.info(f"FakeLLM received query: {query}")

        class Response:
            response = f"ack: {query}"

        return Response()


class ChatAgentManager:
    def __init__(
        self,
        llm: Any,  # LiteLLM instance, must be compatible with llama-index LLM interface
        thread_id: int,
        user_id: str,
        max_tokens: int = 2048,
        tools: Optional[List[Callable]] = None,
        subagents: Optional[List[Callable]] = None,
    ):
        self._using_fake_llm = llm is None

        # If llm is None, always use FakeLLM
        if self._using_fake_llm:
            logger.warning(
                "llm=None was explicitly passed. Using FakeLLM in offline mode."
            )
            self.llm = FakeLLM()
        else:
            self.llm = llm
            logger.info("Using provided LLM instance")

        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.tools = tools or []
        self.subagents = subagents or []
        self.agent: Optional[FunctionCallingAgent] = None
        self.memory: Optional[ChatMemoryBuffer] = None
        logger.info(
            f"ChatAgentManager initialized for user_id={self.user_id}, thread_id={self.thread_id}, "
            f"max_tokens={self.max_tokens}, tools={len(self.tools)}, subagents={len(self.subagents)}, "
            f"using_fake_llm={self._using_fake_llm}"
        )

    async def get_memory(self, user_input: str = "") -> List[Dict[str, Any]]:
        logger.debug(
            f"Retrieving memory for thread_id={self.thread_id} with user_input='{user_input}'"
        )
        messages = await history_manager.get_thread_history(self.thread_id, limit=100)
        # Reverse to chronological order (oldest to newest)
        messages = list(reversed(messages))
        msg_dicts = [
            m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in messages
        ]
        selected = context_module.select_relevant_messages(
            msg_dicts,
            user_input=user_input,
            max_tokens=self.max_tokens,
            model=os.environ.get("LLM_MODEL", ""),
        )
        logger.debug(f"Selected {len(selected)} relevant messages for memory context")
        return selected

    async def build_agent(self, user_input: str = ""):
        logger.info(
            f"Building agent for thread_id={self.thread_id} with user_input='{user_input}'"
        )
        # Wrap tools and subagents as FunctionTool
        all_tools: List[BaseTool] = []
        for t in self.tools + self.subagents:
            all_tools.append(FunctionTool.from_defaults(fn=t))
        # Prepare memory buffer from context
        memory_msgs = await self.get_memory(user_input)
        chat_history = [
            ChatMessage(
                role="user" if m.get("user_id") == self.user_id else "assistant",
                content=m["content"],
            )
            for m in memory_msgs
        ]
        self.memory = ChatMemoryBuffer.from_defaults(chat_history=chat_history)
        self.agent = FunctionCallingAgent.from_tools(
            tools=all_tools,
            llm=self.llm,
            memory=self.memory,
            max_function_calls=5,
        )
        logger.info(
            f"Agent built with {len(all_tools)} tools and {len(chat_history)} chat history messages"
        )

    async def chat(self, user_input: str) -> str:
        """Process a chat message from the user and return the assistant's response.

        Args:
            user_input: The message from the user

        Returns:
            The assistant's response

        Raises:
            ValueError: If no LLM is available and not in fake mode
            Exception: Any exception raised by the LLM
        """
        logger.info(
            f"Chat called for thread_id={self.thread_id}, user_id={self.user_id} with input: {user_input}"
        )

        # Ensure thread exists and get thread object
        from ormar.exceptions import NoMatch

        try:
            thread = await history_manager.Thread.objects.get(id=self.thread_id)
        except NoMatch:
            logger.warning(
                f"Thread id={self.thread_id} not found. Creating new thread for user_id={self.user_id}"
            )
            thread = await history_manager.create_thread(self.user_id)
            self.thread_id = thread.id

        # Persist user message
        await history_manager.append_message(self.thread_id, self.user_id, user_input)

        # Handle fake LLM mode
        if self._using_fake_llm or isinstance(self.llm, FakeLLM):
            response = f"ack: {user_input}"
            await history_manager.append_message(self.thread_id, "assistant", response)
            logger.info(f"FakeLLM response: {response}")
            return response

        # Validate LLM is available
        if self.llm is None:
            error_msg = "No LLM instance provided and not in fake mode"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize agent if needed
        if self.agent is None:
            logger.debug("Agent not built yet. Building agent...")
            await self.build_agent(user_input)

        # Process with real LLM
        try:
            response = await self.agent.achat(user_input)  # type: ignore[union-attr]
            response_text = (
                str(response.response)
                if hasattr(response, "response")
                else str(response)
            )
            logger.info(f"Agent response: {response_text}")

            # Persist the assistant's response
            await history_manager.append_message(
                self.thread_id, "assistant", response_text
            )
            return response_text

        except Exception as e:
            logger.error(f"Error during agent.achat: {e}", exc_info=True)
            raise


# Example usage (async context):
# manager = ChatAgentManager(llm=your_litellm, thread_id=1, user_id="user1", tools=[calendar_tool], subagents=[email_tool])
# await manager.build_agent(user_input="What's on my calendar?")
# reply = await manager.chat("What's on my calendar?")
# print(reply)
