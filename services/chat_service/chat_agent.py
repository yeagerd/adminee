# chat_agent.py
"""
Modern chat agent implementation using current best-practices llama-index memory.

This implementation uses:
- StaticMemoryBlock: For persistent system information
- FactExtractionMemoryBlock: For extracting facts from conversations
- VectorMemoryBlock: For semantic search over conversation history
- Integration with history_manager for database persistence

This file contains the actual agent implementation while llama_manager.py
handles orchestration across multiple agents.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

import history_manager
from llm_manager import FakeLLM, llm_manager

from llama_index.core import StorageContext
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.function_calling import FunctionCallingAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole

# FakeLLM is defined in llm_manager.py
from llama_index.core.memory import (
    BaseMemoryBlock,
    FactExtractionMemoryBlock,
    Memory,
    StaticMemoryBlock,
    VectorMemoryBlock,
)
from llama_index.core.tools import FunctionTool
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Modern chat agent with explicit llama-index memory blocks.

    Features:
    - StaticMemoryBlock for system instructions
    - FactExtractionMemoryBlock for conversation facts
    - VectorMemoryBlock for semantic conversation search
    - Database integration for conversation persistence
    """

    def __init__(
        self,
        thread_id: int,
        user_id: str,
        max_tokens: int = 30000,
        chat_history_token_ratio: float = 0.7,
        token_flush_size: int = 3000,
        tools: Optional[List[Callable]] = None,
        subagents: Optional[List[Callable]] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        static_content: Optional[str] = None,
        enable_fact_extraction: bool = True,
        enable_vector_memory: bool = True,
        max_facts: int = 50,
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.chat_history_token_ratio = chat_history_token_ratio
        self.token_flush_size = token_flush_size

        # Agent configuration
        self.tools = tools or []
        self.subagents = subagents or []
        self.static_content = static_content
        self.enable_fact_extraction = enable_fact_extraction
        self.enable_vector_memory = enable_vector_memory
        self.max_facts = max_facts

        # LLM configuration
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs or {}

        # Initialize LLM instance
        self.llm = llm_manager.get_llm(
            model=llm_model, provider=llm_provider, **self.llm_kwargs
        )

        # Agent components (initialized during build)
        self.storage_context: Optional[StorageContext] = None
        self.memory: Optional[Memory] = None
        self.agent: Optional[Any] = None

        logger.info(
            f"ModernChatAgent initialized for user_id={self.user_id}, "
            f"thread_id={self.thread_id}, fact_extraction={self.enable_fact_extraction}, "
            f"vector_memory={self.enable_vector_memory}"
        )

    def _create_storage_context(self) -> StorageContext:
        """Create storage context for vector memory."""
        vector_store = SimpleVectorStore()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        logger.debug("Created storage context with SimpleVectorStore")
        return storage_context

    def _create_memory_blocks(self) -> List[BaseMemoryBlock]:
        """Create memory blocks based on configuration."""
        memory_blocks = []

        # 1. Static Memory Block (priority 0)
        static_content = self.static_content or self._get_default_static_content()
        from llama_index.core.base.llms.types import TextBlock

        static_block = StaticMemoryBlock(
            static_content=[TextBlock(text=static_content)], priority=0
        )
        memory_blocks.append(static_block)
        logger.debug("Created StaticMemoryBlock")

        # 2. Fact Extraction Memory Block (priority 1)
        if self.enable_fact_extraction:
            try:
                fact_block = FactExtractionMemoryBlock(
                    llm=self.llm,
                    priority=1,
                    max_facts=self.max_facts,
                )
                memory_blocks.append(fact_block)
                logger.debug("Created FactExtractionMemoryBlock")
            except Exception as e:
                logger.warning(f"Failed to create FactExtractionMemoryBlock: {e}")

        # 3. Vector Memory Block (priority 2)
        if self.enable_vector_memory:
            try:
                # Get embedding model - use OpenAI by default
                embed_model = OpenAIEmbedding(
                    model="text-embedding-3-small",
                    api_key=os.environ.get("OPENAI_API_KEY"),
                )

                vector_store = (
                    self.storage_context.vector_store if self.storage_context else None
                )
                if vector_store is None:
                    raise ValueError("Vector store not available")
                vector_block = VectorMemoryBlock(
                    name="conversation_history",
                    vector_store=vector_store,
                    priority=2,
                    embed_model=embed_model,
                    similarity_top_k=3,
                    retrieval_context_window=5,
                )
                memory_blocks.append(vector_block)
                logger.debug("Created VectorMemoryBlock")
            except Exception as e:
                logger.warning(
                    f"Failed to create VectorMemoryBlock: {e}. "
                    "Vector memory will be disabled for this session."
                )
                # Continue without vector memory

        logger.info(f"Created {len(memory_blocks)} memory blocks")
        return memory_blocks

    def _get_default_static_content(self) -> str:
        """Get default static content for the system memory block."""
        return (
            f"You are a helpful AI assistant. You are conversing with user {self.user_id}. "
            "You have access to tools and can help with various tasks including email, calendar, "
            "and document management. Always be helpful, accurate, and professional."
        )

    async def _load_chat_history_from_db(self) -> List[ChatMessage]:
        """Load chat history from database and convert to llama-index format."""
        try:
            # Get messages from database
            db_messages = await history_manager.get_thread_history(
                self.thread_id, limit=100
            )

            # Reverse to chronological order (oldest to newest)
            db_messages = list(reversed(db_messages))

            # Convert to llama-index ChatMessage format
            chat_history = []
            for msg in db_messages:
                role = (
                    MessageRole.USER
                    if msg.user_id == self.user_id
                    else MessageRole.ASSISTANT
                )
                chat_message = ChatMessage(
                    role=role,
                    content=msg.content,
                )
                chat_history.append(chat_message)

            logger.info(f"Loaded {len(chat_history)} messages from database")
            return chat_history

        except Exception as e:
            logger.error(f"Error loading chat history from database: {e}")
            return []

    async def build_agent(self, user_input: str = "") -> None:
        """Build or rebuild the agent with the latest context and memory blocks."""
        logger.info("Building modern chat agent with memory blocks...")

        # Create storage context
        self.storage_context = self._create_storage_context()

        # Create memory blocks
        memory_blocks = self._create_memory_blocks()

        # Load existing chat history from database
        chat_history = await self._load_chat_history_from_db()

        # Create memory with blocks
        from llama_index.core.memory.memory import InsertMethod

        self.memory = Memory.from_defaults(
            session_id=f"thread_{self.thread_id}",
            token_limit=self.max_tokens,
            chat_history_token_ratio=self.chat_history_token_ratio,
            token_flush_size=self.token_flush_size,
            memory_blocks=memory_blocks,
            insert_method=InsertMethod.USER,  # Insert memory into user messages
            chat_history=chat_history,
        )

        # Build tools list
        all_tools = []

        # Validate and register tools
        if self.tools:
            for tool in self.tools:
                if tool is None:
                    logger.warning("Skipping None tool in tools list")
                    continue
                try:
                    tool_instance = FunctionTool.from_defaults(fn=tool)
                    all_tools.append(tool_instance)
                    logger.debug(f"Registered tool: {tool_instance.metadata.name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool}: {str(e)}")

        # Validate and register subagents
        if self.subagents:
            for agent in self.subagents:
                if agent is None:
                    logger.warning("Skipping None agent in subagents list")
                    continue
                try:
                    agent_instance = FunctionTool.from_defaults(fn=agent)
                    all_tools.append(agent_instance)
                    logger.debug(f"Registered subagent: {agent_instance.metadata.name}")
                except Exception as e:
                    logger.error(f"Failed to register subagent {agent}: {str(e)}")

        # Create agent based on whether we have tools
        if all_tools:
            # Use FunctionCallingAgent if we have tools
            self.agent = FunctionCallingAgent.from_tools(
                tools=all_tools,
                llm=self.llm,
                max_function_calls=5,
            )
            logger.info(f"Built FunctionCallingAgent with {len(all_tools)} tools")
        else:
            # Use ReActAgent if no tools - handle FakeLLM compatibility
            try:
                self.agent = ReActAgent.from_tools(
                    tools=[], llm=self.llm, memory=self.memory, verbose=True
                )
                logger.info("Built ReActAgent (no tools configured)")
            except AttributeError as e:
                if "context_window" in str(e):
                    # Fall back to basic agent creation when using FakeLLM
                    from llama_index.core.memory.chat_memory_buffer import (
                        ChatMemoryBuffer,
                    )

                    basic_memory = ChatMemoryBuffer.from_defaults()
                    self.agent = ReActAgent.from_tools(
                        tools=[], llm=self.llm, memory=basic_memory, verbose=True
                    )
                    logger.warning("Using basic memory due to FakeLLM limitations")
                else:
                    raise

        logger.info(
            f"Agent built successfully with {len(memory_blocks)} memory blocks, "
            f"{len(chat_history)} chat history messages"
        )

    async def chat(self, user_input: str) -> str:
        """Process a chat message from the user and return the assistant's response."""
        logger.info(
            f"Chat called for thread_id={self.thread_id}, user_id={self.user_id} "
            f"with input: {user_input}"
        )

        # Ensure thread exists
        thread = await history_manager.get_thread(self.thread_id)
        if thread is None:
            logger.warning(
                f"Thread id={self.thread_id} not found. Creating new thread for user_id={self.user_id}"
            )
            thread = await history_manager.create_thread(self.user_id)
            self.thread_id = int(thread.id)  # Ensure proper type

        # Handle fake LLM mode
        if isinstance(self.llm, FakeLLM):
            from llama_index.core.llms import ChatMessage, MessageRole

            response_obj = await self.llm.achat(
                [ChatMessage(role=MessageRole.USER, content=user_input)]
            )
            response = response_obj.content or ""
            await history_manager.append_message(self.thread_id, "assistant", response)
            logger.info(f"FakeLLM response: {response}")
            return response

        # Validate LLM is available
        if self.llm is None:
            error_msg = "No LLM instance provided and not in fake mode"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize agent if needed
        if self.agent is None or self.memory is None:
            logger.debug("Agent not built yet. Building agent...")
            await self.build_agent(user_input)

        try:
            # Persist user message to database first
            await history_manager.append_message(
                self.thread_id, self.user_id, user_input
            )

            # Process with the agent using memory
            if self.agent is not None:
                # Use chat method for agents (both ReActAgent and FunctionCallingAgent support this)
                response = await self.agent.achat(user_input)
                response_text = (
                    str(response.response)
                    if hasattr(response, "response")
                    else str(response)
                )
            else:
                response_text = "Error: Agent not available"

            logger.info(f"Agent response: {response_text}")

            # Persist the assistant's response
            await history_manager.append_message(
                self.thread_id, "assistant", response_text
            )

            return response_text

        except Exception as e:
            logger.error(f"Error during agent.run: {e}", exc_info=True)
            raise

    async def get_memory_info(self) -> Dict[str, Any]:
        """Get information about the current memory state for debugging."""
        if not self.memory:
            return {"error": "Memory not initialized"}

        try:
            # Get current memory content
            current_memory = await self.memory.aget()

            info: Dict[str, Any] = {
                "session_id": getattr(self.memory, "session_id", "unknown"),
                "token_limit": getattr(self.memory, "token_limit", "unknown"),
                "current_messages": len(current_memory),
                "memory_blocks": [],
            }

            # Get info about memory blocks
            if hasattr(self.memory, "memory_blocks"):
                for block in self.memory.memory_blocks:
                    block_info = {
                        "name": getattr(block, "name", "unknown"),
                        "priority": getattr(block, "priority", "unknown"),
                        "type": type(block).__name__,
                    }

                    # Add specific info for fact extraction blocks
                    if hasattr(block, "facts"):
                        if hasattr(block.facts, "append"):
                            block_info["facts_count"] = len(block.facts)
                            block_info["facts"] = block.facts[:5]  # First 5 facts

                    info["memory_blocks"].append(block_info)

            return info

        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {"error": str(e)}

    async def reset_memory(self) -> None:
        """Reset the memory state."""
        if self.memory:
            await self.memory.areset()
            logger.info("Memory reset successfully")
        else:
            logger.warning("No memory to reset")


# Factory function for backward compatibility
def create_chat_agent(
    thread_id: int,
    user_id: str,
    max_tokens: int = 30000,
    tools: Optional[List[Callable]] = None,
    subagents: Optional[List[Callable]] = None,
    llm_model: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> ChatAgent:
    """Factory function to create a modern chat agent."""
    return ChatAgent(
        thread_id=thread_id,
        user_id=user_id,
        max_tokens=max_tokens,
        tools=tools,
        subagents=subagents,
        llm_model=llm_model,
        llm_provider=llm_provider,
        llm_kwargs=llm_kwargs,
        **kwargs,
    )


# Example usage:
# agent = create_chat_agent(
#     thread_id=1,
#     user_id="user123",
#     tools=[calendar_tool, email_tool],
#     static_content="You are a productivity assistant.",
#     enable_fact_extraction=True,
#     enable_vector_memory=True,
# )
# await agent.build_agent()
# response = await agent.chat("What's on my calendar today?")
