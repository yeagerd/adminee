"""
Workflow-based chat agent implementation using LlamaIndex Workflow system.

This module implements a modern chat agent using the LlamaIndex Workflow architecture
with event-driven step orchestration for sophisticated conversation handling.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent
from llama_index.core.llms import LLM

from .steps.planner_step import PlannerStep
from .steps.tool_executor_step import ToolExecutorStep
from .steps.clarifier_step import ClarifierStep
from .steps.draft_builder_step import DraftBuilderStep
from .events import (
    UserInputEvent,
    DraftCreatedEvent,
    WorkflowMetadata
)
from .llm_manager import get_llm_manager

logger = logging.getLogger(__name__)


class WorkflowChatAgent(Workflow):
    """
    LlamaIndex Workflow-based chat agent with sophisticated event routing.
    
    This agent orchestrates conversation handling through a series of specialized
    workflow steps that communicate via typed events.
    """
    
    def __init__(
        self,
        thread_id: int,
        user_id: str,
        llm_model: str,
        llm_provider: str,
        tools: Optional[List[Any]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.thread_id = thread_id
        self.user_id = user_id
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        
        # Initialize LLM
        self.llm = get_llm_manager().get_llm(
            model=llm_model, 
            provider=llm_provider
        )
        
        # Initialize workflow steps
        self.planner_step = PlannerStep(llm=self.llm)
        self.tool_executor_step = ToolExecutorStep(llm=self.llm, tools=tools or [])
        self.clarifier_step = ClarifierStep(llm=self.llm)
        self.draft_builder_step = DraftBuilderStep(llm=self.llm)
        
        # Add steps to workflow
        self.add_step(self.planner_step)
        self.add_step(self.tool_executor_step)
        self.add_step(self.clarifier_step)
        self.add_step(self.draft_builder_step)
        
        logger.info(f"WorkflowChatAgent initialized for thread_id={thread_id}, user_id={user_id}")
    
    async def chat(self, user_input: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process user input through the workflow and return the response.
        
        Args:
            user_input: The user's message
            conversation_history: Previous conversation messages
            
        Returns:
            The agent's response
        """
        try:
            # Create initial user input event
            user_event = UserInputEvent(
                event_id=f"user_input_{datetime.now().timestamp()}",
                thread_id=self.thread_id,
                user_id=self.user_id,
                message=user_input,
                conversation_history=conversation_history or [],
                metadata=WorkflowMetadata(
                    timestamp=datetime.now(),
                    source="workflow_agent",
                    priority="normal"
                )
            )
            
            # Run the workflow
            result = await self.run(user_input=user_event)
            
            # Extract response from result
            if isinstance(result, DraftCreatedEvent):
                return result.draft_content
            elif hasattr(result, 'response'):
                return result.response
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Error in workflow chat: {e}")
            return f"I apologize, but I encountered an error processing your request: {str(e)}"
    
    async def run(self, user_input: UserInputEvent) -> Any:
        """
        Main workflow entry point.
        
        This method is called by the LlamaIndex Workflow system and orchestrates
        the conversation through the various workflow steps.
        """
        # The workflow steps will handle the event routing automatically
        # based on their @step decorators and event type matching
        return await super().run(user_input=user_input)


def create_workflow_chat_agent(
    thread_id: int,
    user_id: str,
    llm_model: str,
    llm_provider: str,
    tools: Optional[List[Any]] = None,
    **kwargs
) -> WorkflowChatAgent:
    """
    Factory function to create a workflow-based chat agent.
    
    Args:
        thread_id: The conversation thread ID
        user_id: The user ID
        llm_model: The LLM model to use
        llm_provider: The LLM provider
        tools: Optional list of tools to make available
        **kwargs: Additional configuration options
        
    Returns:
        Configured WorkflowChatAgent instance
    """
    return WorkflowChatAgent(
        thread_id=thread_id,
        user_id=user_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        tools=tools,
        **kwargs
    ) 