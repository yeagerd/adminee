# llama_manager.py
"""
Planning agent for chat_service using LiteLLM and llama-index.
Implements agent loop, tool/subagent registration, and token-constrained memory.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from llama_index.core.agent.function_calling import FunctionCallingAgent
from llama_index.core.agent import ReActAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.types import BaseTool

from services.chat_service import context_module, history_manager

from .llm_manager import llm_manager

logger = logging.getLogger(__name__)


from .llm_manager import FakeLLM


class ChatAgentManager:
    def __init__(
        self,
        thread_id: int,
        user_id: str,
        max_tokens: int = 2048,
        tools: Optional[List[Callable]] = None,
        subagents: Optional[List[Callable]] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs or {}

        # Initialize LLM instance
        self.llm = llm_manager.get_llm(
            model=llm_model, provider=llm_provider, **self.llm_kwargs
        )

        logger.info(
            f"Initialized ChatAgentManager with model={llm_model or 'default'}, "
            f"provider={llm_provider or 'default'}"
        )

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
            f"model={self.llm_model or 'default'}, provider={self.llm_provider or 'default'}"
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

        # Get model from instance or environment
        model = getattr(self, "llm_model", None) or os.environ.get(
            "LLM_MODEL", "gpt-3.5-turbo"
        )

        # Pass LLM kwargs if available
        llm_kwargs = getattr(self, "llm_kwargs", {})

        # Use dynamic context selection which can use LLM for better context selection
        selected = await context_module.dynamic_context_selection(
            messages=msg_dicts,
            user_input=user_input,
            thread_state=None,  # Can be enhanced with thread state in the future
            max_tokens=self.max_tokens,
            model=model,
            **llm_kwargs,
        )

        logger.debug(f"Selected {len(selected)} relevant messages for memory context")
        return selected

    async def build_agent(self, user_input: str) -> None:
        """Build or rebuild the agent with the latest context and tools."""
        # Get relevant context and chat history
        context_messages = await self.get_memory(user_input)
        chat_history = await history_manager.get_thread_history(self.thread_id, limit=100)
        # Reverse to chronological order (oldest to newest)
        chat_history = list(reversed(chat_history))
        msg_dicts = [
            m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in chat_history
        ]

        # Combine context and chat history
        memory_msgs = context_messages + msg_dicts
        
        # Convert messages to llama-index format
        from llama_index.core.base.llms.types import MessageRole
        chat_history = [
            ChatMessage(
                role=MessageRole.USER if m.get("user_id") == self.user_id else MessageRole.ASSISTANT,
                content=m["content"],
            )
            for m in memory_msgs
        ]
        
        # Create memory
        self.memory = ChatMemoryBuffer.from_defaults(chat_history=chat_history)
        
        # Build tools list
        all_tools = []
        if self.tools:
            all_tools.extend([FunctionTool.from_defaults(fn=tool) for tool in self.tools])
        if self.subagents:
            all_tools.extend([FunctionTool.from_defaults(fn=agent) for agent in self.subagents])
        
        if all_tools:
            # If we have tools, use FunctionCallingAgent
            self.agent = FunctionCallingAgent.from_tools(
                tools=all_tools,
                llm=self.llm,
                memory=self.memory,
                max_function_calls=5,
            )
            logger.info(f"Built FunctionCallingAgent with {len(all_tools)} tools and {len(chat_history)} messages of chat history")
        else:
            # If no tools, use ReActAgent
            self.agent = ReActAgent.from_tools(
                tools=[],
                llm=self.llm,
                memory=self.memory,
                verbose=True
            )
            logger.info(
                f"Built ReActAgent with {len(chat_history)} chat history messages (no tools configured)"
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
        if isinstance(self.llm, FakeLLM):
            # If we're using FakeLLM, just return a simple response
            response_obj = await self.llm.achat(
                [{"role": "user", "content": user_input}]
            )
            response = response_obj.content
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
