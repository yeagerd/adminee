"""
LlamaIndex AgentWorkflow implementation for chat_service.

This module provides a workflow-based agent architecture using LlamaIndex's AgentWorkflow
and FunctionAgent. It integrates with the existing ChatAgent and LLM manager infrastructure
while providing modern workflow capabilities including:

- AgentWorkflow orchestration
- Context and state management
- Streaming support
- Human-in-the-loop capabilities
- Tool integration from existing llm_tools
- Memory persistence through history_manager

This will eventually supersede the llama_manager.py orchestration layer.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context, Event, InputRequiredEvent, HumanResponseEvent

from services.chat import history_manager
from services.chat.agents.chat_agent import ChatAgent
from services.chat.agents.llm_manager import get_llm_manager
from services.chat.agents.llm_tools import get_tool_registry, ToolRegistry

logger = logging.getLogger(__name__)


class WorkflowAgent:
    """
    LlamaIndex AgentWorkflow-based chat agent.
    
    This class provides a modern workflow-based architecture that:
    - Uses AgentWorkflow for orchestration
    - Integrates with existing ChatAgent for memory management
    - Supports context persistence and state management
    - Provides streaming and human-in-the-loop capabilities
    - Uses existing LLM manager and tools
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

        # Initialize tools
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
        self.function_agent: Optional[FunctionAgent] = None
        self.agent_workflow: Optional[AgentWorkflow] = None
        self.context: Optional[Context] = None

        logger.info(
            f"WorkflowAgent initialized for user_id={self.user_id}, "
            f"thread_id={self.thread_id}, tools_count={len(self.tools)}"
        )

    def _prepare_tools(self, tools: Optional[List[Union[Callable, FunctionTool]]]) -> List[FunctionTool]:
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
        """Get default system prompt for the workflow agent."""
        return (
            f"You are a helpful AI assistant. You are conversing with user {self.user_id}. "
            "You have access to tools and can help with various tasks including email, calendar, "
            "and document management. Always be helpful, accurate, and professional. "
            "When using tools, provide clear explanations of what you're doing and why."
        )

    async def build_agent(self, user_input: str = "") -> None:
        """
        Build the agent workflow components.
        
        This method initializes:
        - The underlying ChatAgent for memory management
        - FunctionAgent with tools and LLM
        - AgentWorkflow for orchestration
        - Context for state management
        """
        try:
            # Build the underlying ChatAgent for memory management
            await self.chat_agent.build_agent(user_input)
            
            # Get all available tools (custom tools + office tools)
            all_tools = self.tools.copy()
            
            # Add office service tools from the registry
            office_tools = list(self.tool_registry._tools.values())
            all_tools.extend(office_tools)

            # Create FunctionAgent with all tools
            system_prompt = self.static_content or self._get_default_system_prompt()
            
            self.function_agent = FunctionAgent(
                tools=all_tools,
                llm=self._llm,
                system_prompt=system_prompt,
            )

            # Create AgentWorkflow with the FunctionAgent
            self.agent_workflow = AgentWorkflow(
                agents=[self.function_agent],
                initial_state={
                    "thread_id": self.thread_id,
                    "user_id": self.user_id,
                    "conversation_history": [],
                }
            )

            # Create context for state management
            self.context = Context(self.agent_workflow)
            
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
            
            # Store in workflow context state
            state = await self.context.get("state", {})
            state["conversation_history"] = [
                {
                    "role": str(msg.role).lower(),
                    "content": msg.content,
                }
                for msg in chat_history
            ]
            await self.context.set("state", state)
            
            logger.debug(f"Loaded {len(chat_history)} messages into workflow context")
            
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
            await history_manager.save_message(
                thread_id=self.thread_id,
                user_id=self.user_id,
                content=user_input,
                role="user"
            )

            # Run the workflow
            response = await self.agent_workflow.run(
                user_msg=user_input, 
                ctx=self.context
            )
            
            # Extract response content
            response_content = str(response) if response else "I'm sorry, I couldn't process your request."

            # Save assistant response to database
            await history_manager.save_message(
                thread_id=self.thread_id,
                user_id="assistant",  # Assistant messages use "assistant" as user_id
                content=response_content,
                role="assistant"
            )

            # Update ChatAgent memory with the new exchange
            if self.chat_agent.memory:
                user_message = ChatMessage(role=MessageRole.USER, content=user_input)
                assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=response_content)
                
                # Add to memory blocks
                await self.chat_agent.memory.put_messages([user_message, assistant_message])

            return response_content

        except Exception as e:
            logger.error(f"Error in chat workflow: {e}")
            # Fallback to a generic error response
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            
            # Still save the error interaction to maintain conversation continuity
            try:
                await history_manager.save_message(
                    thread_id=self.thread_id,
                    user_id="assistant",
                    content=error_response,
                    role="assistant"
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
            await history_manager.save_message(
                thread_id=self.thread_id,
                user_id=self.user_id,
                content=user_input,
                role="user"
            )

            # Run workflow with streaming
            handler = self.agent_workflow.run(user_msg=user_input, ctx=self.context)
            
            full_response = ""
            async for event in handler.stream_events():
                yield event
                # Collect the full response for database storage
                if hasattr(event, 'delta') and event.delta:
                    full_response += event.delta

            # Wait for final response
            final_response = await handler
            if not full_response:
                full_response = str(final_response)

            # Save assistant response to database
            await history_manager.save_message(
                thread_id=self.thread_id,
                user_id="assistant",
                content=full_response,
                role="assistant"
            )

            # Update ChatAgent memory
            if self.chat_agent.memory and full_response:
                user_message = ChatMessage(role=MessageRole.USER, content=user_input)
                assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=full_response)
                await self.chat_agent.memory.put_messages([user_message, assistant_message])

        except Exception as e:
            logger.error(f"Error in stream chat workflow: {e}")
            error_response = "I apologize, but I encountered an error processing your request."
            
            # Save error response
            try:
                await history_manager.save_message(
                    thread_id=self.thread_id,
                    user_id="assistant",
                    content=error_response,
                    role="assistant"
                )
            except:
                pass
            
            # Yield error event
            yield {"error": str(e), "message": error_response}

    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information from the underlying ChatAgent."""
        if self.chat_agent:
            return await self.chat_agent.get_memory_info()
        return {"error": "Agent not initialized"}

    async def reset_memory(self) -> None:
        """Reset memory in the underlying ChatAgent."""
        if self.chat_agent:
            await self.chat_agent.reset_memory()
        
        # Also reset workflow context
        if self.context:
            self.context = Context(self.agent_workflow)

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
            self.agent_workflow, 
            context_dict, 
            serializer=JsonSerializer()
        )

    # Properties for compatibility with existing code
    @property
    def llm(self):
        """Access to the LLM instance."""
        return self._llm

    @property
    def agent(self):
        """Access to the function agent."""
        return self.function_agent

    @property
    def memory(self):
        """Access to the ChatAgent's memory."""
        return self.chat_agent.memory if self.chat_agent else None 