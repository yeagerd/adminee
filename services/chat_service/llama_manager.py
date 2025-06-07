# llama_manager.py
"""
Planning agent for chat_service using LiteLLM and llama-index.
Implements agent loop, tool/subagent registration, and token-constrained memory.
"""

from typing import Any, Callable, Dict, List, Optional

from llama_index.core.agent.function_calling.base import FunctionCallingAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool

from services.chat_service import context_module, history_manager


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
        self.llm = llm
        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.tools = tools or []
        self.subagents = subagents or []
        self.agent = None
        self.memory = None

    async def get_memory(self, user_input: str = "") -> List[Dict[str, Any]]:
        messages = await history_manager.get_thread_history(self.thread_id, limit=100)
        msg_dicts = [
            m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in messages
        ]
        selected = context_module.select_relevant_messages(
            msg_dicts, user_input=user_input, max_tokens=self.max_tokens
        )
        return selected

    async def build_agent(self, user_input: str = ""):
        # Wrap tools and subagents as FunctionTool
        all_tools = []
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

    async def chat(self, user_input: str) -> str:
        if self.agent is None:
            await self.build_agent(user_input)
        # Run the agent with the user input
        response = await self.agent.achat(user_input)
        # Persist user message
        await history_manager.append_message(self.thread_id, self.user_id, user_input)
        # Persist agent response
        await history_manager.append_message(
            self.thread_id, "assistant", response.response
        )
        return response.response


# Example usage (async context):
# manager = ChatAgentManager(llm=your_litellm, thread_id=1, user_id="user1", tools=[calendar_tool], subagents=[email_tool])
# await manager.build_agent(user_input="What's on my calendar?")
# reply = await manager.chat("What's on my calendar?")
# print(reply)
