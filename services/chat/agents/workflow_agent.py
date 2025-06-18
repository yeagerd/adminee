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
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import (
    Context,
)

from services.chat import history_manager
from services.chat.agents.calendar_agent import CalendarAgent
from services.chat.agents.chat_agent import ChatAgent

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
        office_service_url: str = "http://localhost:8001",
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.chat_history_token_ratio = chat_history_token_ratio
        self.token_flush_size = token_flush_size
        self.office_service_url = office_service_url

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
        self.tool_registry = get_tool_registry(office_service_url=office_service_url)

        # Create ChatAgent for memory management (leveraging existing implementation)
        self.chat_agent = ChatAgent(
            thread_id=thread_id,
            user_id=user_id,
            llm_model=llm_model,
            llm_provider=llm_provider,
            max_tokens=max_tokens,
            chat_history_token_ratio=chat_history_token_ratio,
            token_flush_size=token_flush_size,
            tools=[],  # Tools will be handled by workflow
            llm_kwargs=llm_kwargs,
            static_content=static_content,
            enable_fact_extraction=enable_fact_extraction,
            enable_vector_memory=enable_vector_memory,
            max_facts=max_facts,
        )

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
            office_service_url=self.office_service_url,
            **self.llm_kwargs,
        )

        agents["EmailAgent"] = EmailAgent(
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
            office_service_url=self.office_service_url,
            **self.llm_kwargs,
        )

        agents["DocumentAgent"] = DocumentAgent(
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
            office_service_url=self.office_service_url,
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
            # Build the underlying ChatAgent for memory management
            await self.chat_agent.build_agent(user_input)

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
                if not hasattr(self.context, 'get') or not hasattr(self.context, 'set'):
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
            # Get messages from database via ChatAgent
            chat_history = await self.chat_agent._load_chat_history_from_db()

            # Store in workflow context state with proper error handling
            try:
                # Check if context has the expected methods
                get_method = getattr(self.context, 'get', None)
                set_method = getattr(self.context, 'set', None)
                
                if get_method is None or set_method is None:
                    logger.warning("Context object missing get/set methods")
                    return
                
                # Try to get current state
                logger.debug(f"Calling context.get('state', {{}}) method")
                state_result = get_method("state", {})
                logger.debug(f"Context.get returned: {state_result} (type: {type(state_result)})")
                
                # Handle both sync and async get methods
                if hasattr(state_result, '__await__'):
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
                logger.debug(f"Context.set returned: {set_result} (type: {type(set_result)})")
                
                # Handle both sync and async set methods
                if hasattr(set_result, '__await__'):
                    logger.debug("Context.set result is awaitable, awaiting it...")
                    await set_result
                    logger.debug("Context.set await completed successfully")
                else:
                    logger.debug("Context.set result is not awaitable, operation complete")

                logger.debug(f"Loaded {len(chat_history)} messages into workflow context")
                
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
            logger.debug(f"Starting workflow.run with user_msg='{user_input}' and context={self.context}")
            try:
                response = await self.agent_workflow.run(
                    user_msg=user_input, ctx=self.context
                )
                logger.debug(f"Workflow.run completed successfully with response: {response}")
            except Exception as workflow_error:
                logger.error(f"Workflow.run failed: {workflow_error}")
                logger.error(f"Workflow error traceback:", exc_info=True)
                raise

            # Extract response content
            response_content = (
                str(response)
                if response
                else "I'm sorry, I couldn't process your request."
            )

            # Save assistant response to database
            await history_manager.append_message(
                thread_id=self.thread_id,
                user_id="assistant",  # Assistant messages use "assistant" as user_id
                content=response_content,
            )

            # Update ChatAgent memory with the new exchange
            if self.chat_agent.memory:
                logger.debug("Updating ChatAgent memory with new messages")
                user_message = ChatMessage(role=MessageRole.USER, content=user_input)
                assistant_message = ChatMessage(
                    role=MessageRole.ASSISTANT, content=response_content
                )

                # Add to memory blocks
                try:
                    memory_result = self.chat_agent.memory.put_messages(
                        [user_message, assistant_message]
                    )
                    if hasattr(memory_result, '__await__'):
                        logger.debug("Memory.put_messages is awaitable, awaiting...")
                        await memory_result
                        logger.debug("Memory.put_messages completed successfully")
                    else:
                        logger.debug("Memory.put_messages is not awaitable, completed synchronously")
                except Exception as memory_error:
                    logger.error(f"Memory update failed: {memory_error}")
                    # Don't fail the whole operation for memory errors
            else:
                logger.debug("No ChatAgent memory available, skipping memory update")

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

            # Update ChatAgent memory
            if self.chat_agent.memory and full_response:
                user_message = ChatMessage(role=MessageRole.USER, content=user_input)
                assistant_message = ChatMessage(
                    role=MessageRole.ASSISTANT, content=full_response
                )
                await self.chat_agent.memory.put_messages(
                    [user_message, assistant_message]
                )

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
        """Get memory information from the underlying ChatAgent."""
        if self.chat_agent:
            try:
                memory_info = await self.chat_agent.get_memory_info()
                return memory_info if memory_info is not None else {"error": "No memory info available"}
            except Exception as e:
                logger.error(f"Failed to get memory info: {e}")
                return {"error": f"Failed to get memory info: {str(e)}"}
        return {"error": "Agent not initialized"}

    async def reset_memory(self) -> None:
        """Reset memory in the underlying ChatAgent."""
        if self.chat_agent:
            try:
                reset_result = await self.chat_agent.reset_memory()
                # Ensure the result is handled properly (should be None for reset operations)
            except Exception as e:
                logger.error(f"Failed to reset ChatAgent memory: {e}")

        # Also reset workflow context
        if self.context and self.agent_workflow:
            try:
                self.context = Context(self.agent_workflow)
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
        """Access to the ChatAgent's memory."""
        return self.chat_agent.memory if self.chat_agent else None
