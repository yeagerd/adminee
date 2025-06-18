"""
LlamaIndex Multi-Agent Workflow implementation for chat_service.

This module provides a specialized multi-agent architecture using LlamaIndex's AgentWorkflow
with domain-specific agents. It integrates with the existing ChatAgent and LLM manager
infrastructure while providing modern workflow capabilities including:

- Multi-agent orchestration with specialized agents
- Context and state management across agents
- Streaming support
- Human-in-the-loop capabilities
- Tool integration from existing llm_tools
- Memory persistence through history_manager
- Agent handoff and coordination

Specialized agents include:
- CoordinatorAgent: Orchestrates tasks and handles handoffs
- CalendarAgent: Calendar and scheduling operations
- EmailAgent: Email management operations
- DocumentAgent: Document and note operations
- DraftAgent: Content creation and drafting

This supersedes single-agent approaches with a focused multi-agent architecture.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import (
    Context,
)

from services.chat import history_manager
from services.chat.agents.calendar_agent import CalendarAgent

# Import specialized agents for multi-agent mode
from services.chat.agents.coordinator_agent import CoordinatorAgent
from services.chat.agents.document_agent import DocumentAgent
from services.chat.agents.draft_agent import DraftAgent
from services.chat.agents.email_agent import EmailAgent
from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import get_tool_registry

logger = logging.getLogger(__name__)


class WorkflowAgent:
    """
    LlamaIndex Multi-Agent Workflow chat agent.

    This class provides a specialized multi-agent architecture that:
    - Uses AgentWorkflow for multi-agent orchestration
    - Integrates with existing ChatAgent for memory management
    - Supports context persistence and state management across agents
    - Provides streaming and human-in-the-loop capabilities
    - Uses existing LLM manager and tools
    - Coordinates between specialized domain agents
    - Handles agent handoffs and task delegation
    """

    def __init__(
        self,
        thread_id: int,
        user_id: str,
        llm_model: str,
        llm_provider: str,
        max_tokens: int = 30000,
        chat_history_token_ratio: float = 0.7,
        token_flush_size: int = 3000,
        tools: Optional[List[Union[Callable, FunctionTool]]] = None,
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
        self.static_content = static_content
        self.enable_fact_extraction = enable_fact_extraction
        self.enable_vector_memory = enable_vector_memory
        self.max_facts = max_facts

        # LLM configuration
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs or {}

        # Initialize LLM instance
        self._llm = get_llm_manager().get_llm(
            model=llm_model, provider=llm_provider, **self.llm_kwargs
        )

        # Initialize tools (legacy parameter, not used in multi-agent mode)
        self.tools = self._prepare_tools(tools)

        # Initialize tool registry for additional office tools
        self.tool_registry = get_tool_registry()

        # Store configuration for direct database operations (no ChatAgent needed)
        self.max_tokens = max_tokens
        self.chat_history_token_ratio = chat_history_token_ratio
        self.token_flush_size = token_flush_size
        self.static_content = static_content
        self.enable_fact_extraction = enable_fact_extraction
        self.enable_vector_memory = enable_vector_memory
        self.max_facts = max_facts

        # Workflow components (initialized during build)
        self.agent_workflow: Optional[AgentWorkflow] = None
        self.context: Optional[Context] = None

        # Multi-agent components
        self.specialized_agents: Dict[str, FunctionAgent] = {}

        logger.info(
            f"WorkflowAgent initialized for user_id={self.user_id}, "
            f"thread_id={self.thread_id}, tools_count={len(self.tools)}, "
            "mode=multi_agent"
        )

    def _prepare_tools(
        self, tools: Optional[List[Union[Callable, FunctionTool]]]
    ) -> List[FunctionTool]:
        """Convert tools to FunctionTool format if needed."""
        if not tools:
            return []

        prepared_tools = []
        for tool in tools:
            if isinstance(tool, FunctionTool):
                prepared_tools.append(tool)
            elif callable(tool):
                # Convert callable to FunctionTool
                function_tool = FunctionTool.from_defaults(fn=tool)
                prepared_tools.append(function_tool)
            else:
                logger.warning(f"Unsupported tool type: {type(tool)}")

        return prepared_tools

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the multi-agent workflow."""
        return (
            f"You are a helpful AI assistant coordinator. You are conversing with user {self.user_id}. "
            "You coordinate between specialized agents to help with various tasks including email, calendar, "
            "and document management. Always be helpful, accurate, and professional."
        )

    async def _load_chat_history_from_db(self) -> List:
        """Load chat history from database for workflow context."""
        try:

            from services.chat import history_manager

            # Get messages from database
            db_messages = await history_manager.get_thread_history(
                self.thread_id, limit=100
            )

            # Reverse to chronological order (oldest to newest)
            db_messages = list(reversed(db_messages))

            # Convert to simple format for workflow context
            chat_history = []
            for msg in db_messages:
                role = "user" if msg.user_id == self.user_id else "assistant"
                chat_history.append(
                    {
                        "role": role,
                        "content": msg.content,
                        "timestamp": str(msg.created_at) if msg.created_at else None,
                    }
                )

            logger.debug(f"Loaded {len(chat_history)} messages into workflow context")
            return chat_history

        except Exception as e:
            logger.error(f"Error loading chat history from database: {e}")
            return []

    def _create_specialized_agents(self) -> Dict[str, FunctionAgent]:
        """Create specialized agents for multi-agent mode."""
        agents = {}

        # Create all specialized agents
        agents["Coordinator"] = CoordinatorAgent(
            llm_model=self.llm_model, llm_provider=self.llm_provider, **self.llm_kwargs
        )

        agents["CalendarAgent"] = CalendarAgent(
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
            **self.llm_kwargs,
        )

        agents["EmailAgent"] = EmailAgent(
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
            **self.llm_kwargs,
        )

        agents["DocumentAgent"] = DocumentAgent(
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
            **self.llm_kwargs,
        )

        agents["DraftAgent"] = DraftAgent(
            llm_model=self.llm_model, llm_provider=self.llm_provider, **self.llm_kwargs
        )

        logger.info(f"Created {len(agents)} specialized agents")
        return agents

    async def build_agent(self, user_input: str = "") -> None:
        """
        Build the multi-agent workflow components.

        This method initializes:
        - The underlying ChatAgent for memory management
        - Specialized agents for different domains
        - AgentWorkflow for orchestration
        - Context for state management
        """
        try:
            # Create specialized agents
            self.specialized_agents = self._create_specialized_agents()

            # Create AgentWorkflow with specialized agents
            agents_list = list(self.specialized_agents.values())
            self.agent_workflow = AgentWorkflow(
                agents=agents_list,
                root_agent="Coordinator",  # Coordinator starts first
                initial_state={
                    "thread_id": str(self.thread_id),
                    "user_id": self.user_id,
                    "conversation_history": [],
                    "calendar_info": {},
                    "email_info": {},
                    "document_info": {},
                    "draft_info": {},
                },
            )

            logger.info("Multi-agent workflow created with specialized agents")

            # Create context for state management
            if self.agent_workflow is None:
                raise ValueError("AgentWorkflow is None, cannot create Context")

            try:
                self.context = Context(self.agent_workflow)

                # Verify context was created successfully
                if self.context is None:
                    raise ValueError("Failed to create Context object")

                # Test that context methods are available
                if not hasattr(self.context, "get") or not hasattr(self.context, "set"):
                    logger.warning("Context created but missing expected methods")

            except Exception as context_error:
                logger.error(f"Failed to create Context: {context_error}")
                # Create a minimal context fallback if needed
                self.context = None
                raise ValueError(f"Context creation failed: {context_error}")

            # Load conversation history into context state
            await self._load_conversation_history()

            logger.info("WorkflowAgent built successfully")

        except Exception as e:
            logger.error(f"Failed to build WorkflowAgent: {e}")
            raise

    async def _load_conversation_history(self) -> None:
        """Load conversation history from database into workflow context."""
        if not self.context:
            return

        try:
            # Get messages from database directly
            chat_history = await self._load_chat_history_from_db()

            # Store in workflow context state with proper error handling
            try:
                # Check if context has the expected methods
                get_method = getattr(self.context, "get", None)
                set_method = getattr(self.context, "set", None)

                if get_method is None or set_method is None:
                    logger.warning("Context object missing get/set methods")
                    return

                # Try to get current state
                logger.debug("Calling context.get('state', {}) method")
                state_result = get_method("state", {})
                logger.debug(
                    f"Context.get returned: {state_result} (type: {type(state_result)})"
                )

                # Handle both sync and async get methods
                if hasattr(state_result, "__await__"):
                    logger.debug("Context.get result is awaitable, awaiting it...")
                    state = await state_result
                    logger.debug(f"Awaited state result: {state}")
                else:
                    logger.debug("Context.get result is not awaitable, using directly")
                    state = state_result

                # Ensure state is a dict
                if not isinstance(state, dict):
                    state = {}

                # Add conversation history
                state["conversation_history"] = [
                    {
                        "role": str(msg.role).lower(),
                        "content": msg.content,
                    }
                    for msg in chat_history
                ]

                # Try to set the state
                logger.debug(f"Calling context.set('state', {state}) method")
                set_result = set_method("state", state)
                logger.debug(
                    f"Context.set returned: {set_result} (type: {type(set_result)})"
                )

                # Handle both sync and async set methods
                if hasattr(set_result, "__await__"):
                    logger.debug("Context.set result is awaitable, awaiting it...")
                    await set_result
                    logger.debug("Context.set await completed successfully")
                else:
                    logger.debug(
                        "Context.set result is not awaitable, operation complete"
                    )

                logger.debug(
                    f"Loaded {len(chat_history)} messages into workflow context"
                )

            except Exception as context_error:
                logger.warning(f"Context operation failed: {context_error}")
                # Continue without context state - the workflow can still function

        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")

    async def chat(self, user_input: str) -> str:
        """
        Process user input through the agent workflow.

        Args:
            user_input: The user's message

        Returns:
            The agent's response
        """
        if not self.agent_workflow or not self.context:
            await self.build_agent(user_input)

        try:
            # Save user message to database
            await history_manager.append_message(
                thread_id=self.thread_id,
                user_id=self.user_id,
                content=user_input,
            )

            # Run the workflow
            logger.debug(
                f"Starting workflow.run with user_msg='{user_input}' and context={self.context}"
            )
            try:
                response = await self.agent_workflow.run(
                    user_msg=user_input, ctx=self.context
                )
                logger.debug(
                    f"Workflow.run completed successfully with response: {response}"
                )
            except Exception as workflow_error:
                logger.error(f"Workflow.run failed: {workflow_error}")
                logger.error("Workflow error traceback:", exc_info=True)
                raise

            # Extract response content
            response_content = (
                str(response)
                if response
                else "I'm sorry, I couldn't process your request."
            )

            # Check for draft information in the workflow context and display it
            try:
                if self.context:
                    # Get current state to check for draft info
                    get_method = getattr(self.context, "get", None)
                    if get_method:
                        state_result = get_method("state", {})
                        # Handle both sync and async get methods
                        if hasattr(state_result, "__await__"):
                            state = await state_result
                        else:
                            state = state_result

                        draft_info = state.get("draft_info", {})
                        if draft_info:
                            logger.info("🎯 DRAFT CREATED - Content visible to client:")
                            draft_summary = []
                            for draft_type, info in draft_info.items():
                                logger.info(f"  📝 {draft_type.upper()}: {info}")
                                draft_summary.append(
                                    f"• {draft_type.replace('_', ' ').title()}: {info}"
                                )

                            # Add draft summary to response if drafts were created
                            if draft_summary:
                                response_content += (
                                    "\n\n📋 **Drafts Created:**\n"
                                    + "\n".join(draft_summary)
                                )
            except Exception as draft_error:
                logger.warning(f"Failed to extract draft information: {draft_error}")

            # Save assistant response to database
            await history_manager.append_message(
                thread_id=self.thread_id,
                user_id="assistant",  # Assistant messages use "assistant" as user_id
                content=response_content,
            )

            # Memory is now handled by the specialized agents in the workflow
            logger.debug(
                "Conversation saved to database, memory handled by workflow agents"
            )

            return response_content

        except Exception as e:
            logger.error(f"Error in chat workflow: {e}")
            # Fallback to a generic error response
            error_response = "I apologize, but I encountered an error processing your request. Please try again."

            # Still save the error interaction to maintain conversation continuity
            try:
                await history_manager.append_message(
                    thread_id=self.thread_id,
                    user_id="assistant",
                    content=error_response,
                )
            except:
                pass  # Don't fail on database save errors

            return error_response

    async def stream_chat(self, user_input: str):
        """
        Stream chat responses from the agent workflow.

        Args:
            user_input: The user's message

        Yields:
            Streaming events from the workflow
        """
        if not self.agent_workflow or not self.context:
            await self.build_agent(user_input)

        try:
            # Save user message to database
            await history_manager.append_message(
                thread_id=self.thread_id,
                user_id=self.user_id,
                content=user_input,
            )

            # Run workflow with streaming
            handler = self.agent_workflow.run(user_msg=user_input, ctx=self.context)

            full_response = ""
            async for event in handler.stream_events():
                yield event
                # Collect the full response for database storage
                if hasattr(event, "delta") and event.delta:
                    full_response += event.delta

            # Wait for final response
            final_response = await handler
            if not full_response:
                full_response = str(final_response)

            # Save assistant response to database
            await history_manager.append_message(
                thread_id=self.thread_id,
                user_id="assistant",
                content=full_response,
            )

            # Memory is handled by the specialized agents in the workflow
            logger.debug("Streaming conversation saved to database")

        except Exception as e:
            logger.error(f"Error in stream chat workflow: {e}")
            error_response = (
                "I apologize, but I encountered an error processing your request."
            )

            # Save error response
            try:
                await history_manager.append_message(
                    thread_id=self.thread_id,
                    user_id="assistant",
                    content=error_response,
                )
            except:
                pass

            # Yield error event
            yield {"error": str(e), "message": error_response}

    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information from the workflow context and specialized agents."""
        try:
            info = {
                "workflow_context": (
                    "initialized" if self.context else "not_initialized"
                ),
                "specialized_agents": (
                    list(self.specialized_agents.keys())
                    if self.specialized_agents
                    else []
                ),
                "thread_id": self.thread_id,
                "user_id": self.user_id,
            }

            # Get conversation history count
            chat_history = await self._load_chat_history_from_db()
            info["conversation_messages"] = len(chat_history)

            return info
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return {"error": f"Failed to get memory info: {str(e)}"}

    async def reset_memory(self) -> None:
        """Reset workflow context (conversation history stays in database)."""
        # Reset workflow context to clear in-memory state
        if self.context and self.agent_workflow:
            try:
                self.context = Context(self.agent_workflow)
                logger.info("Workflow context reset successfully")
            except Exception as e:
                logger.warning(f"Failed to reset workflow context: {e}")
                self.context = None

    # Context management methods
    async def save_context(self) -> Dict[str, Any]:
        """Save the current workflow context to a serializable format."""
        if not self.context:
            return {}

        from llama_index.core.workflow import JsonSerializer

        return self.context.to_dict(serializer=JsonSerializer())

    async def load_context(self, context_dict: Dict[str, Any]) -> None:
        """Load workflow context from a serialized format."""
        if not self.agent_workflow:
            await self.build_agent()

        from llama_index.core.workflow import JsonSerializer

        self.context = Context.from_dict(
            self.agent_workflow, context_dict, serializer=JsonSerializer()
        )

    # Properties for compatibility with existing code
    @property
    def llm(self):
        """Access to the LLM instance."""
        return self._llm

    @property
    def agent(self):
        """Access to the coordinator agent."""
        return self.specialized_agents.get("Coordinator")

    @property
    def memory(self):
        """Access to workflow context for compatibility."""
        return self.context
