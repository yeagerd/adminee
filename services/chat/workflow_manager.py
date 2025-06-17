"""
Workflow-based chat agent manager for chat_service using LlamaIndex Workflow system.

This module provides a drop-in replacement for ChatAgentManager that uses
the new WorkflowChatAgent with event-driven step orchestration.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .workflow_agent import WorkflowChatAgent, create_workflow_chat_agent

logger = logging.getLogger(__name__)


class WorkflowChatAgentManager:
    """
    Drop-in replacement for ChatAgentManager using WorkflowChatAgent.
    
    This manager provides the same interface as the original ChatAgentManager
    but uses the new LlamaIndex Workflow-based agent internally.
    """
    
    def __init__(
        self,
        thread_id: int,
        user_id: str,
        llm_model: str,
        llm_provider: str,
        max_tokens: int = 2048,
        tools: Optional[List[Callable]] = None,
        subagents: Optional[List[Callable]] = None,
        llm_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_kwargs = llm_kwargs or {}
        
        # Store tools and subagents for compatibility
        self.tools = tools or []
        self.subagents = subagents or []
        
        # Initialize workflow agent
        self.workflow_agent: Optional[WorkflowChatAgent] = None
        
        logger.info(
            f"WorkflowChatAgentManager initialized - "
            f"user_id={self.user_id}, thread_id={self.thread_id}, "
            f"tools_count={len(self.tools)}, subagents_count={len(self.subagents)}"
        )
    
    def _ensure_workflow_agent(self) -> WorkflowChatAgent:
        """Ensure the workflow agent is created."""
        if self.workflow_agent is None:
            self.workflow_agent = create_workflow_chat_agent(
                thread_id=self.thread_id,
                user_id=self.user_id,
                llm_model=self.llm_model,
                llm_provider=self.llm_provider,
                tools=self.tools
            )
        return self.workflow_agent
    
    # Public API methods for compatibility with ChatAgentManager
    @property
    def llm(self):
        """Access to the workflow agent's LLM."""
        agent = self._ensure_workflow_agent()
        return agent.llm
    
    @property
    def agent(self):
        """Access to the workflow agent."""
        return self._ensure_workflow_agent()
    
    @agent.setter
    def agent(self, value):
        """Set the workflow agent."""
        self.workflow_agent = value
    
    @property
    def memory(self):
        """Access to the workflow agent's memory (not applicable for workflow)."""
        # Workflow agents don't have traditional memory blocks
        return None
    
    async def get_memory(self, user_input: str = "") -> List[Dict[str, Any]]:
        """
        Get memory information from the workflow agent.
        
        Note: Workflow agents don't use traditional memory blocks,
        so this returns minimal information for compatibility.
        """
        return [
            {
                "agent": "workflow",
                "memory": {
                    "type": "workflow_context",
                    "thread_id": self.thread_id,
                    "user_id": self.user_id,
                    "status": "active"
                }
            }
        ]
    
    async def build_agent(self, user_input: str = "") -> None:
        """Build or rebuild the workflow agent system."""
        logger.info("Building workflow agent system...")
        
        # Ensure workflow agent is created
        self._ensure_workflow_agent()
        
        logger.info("Workflow agent system built successfully")
    
    async def chat(self, user_input: str) -> str:
        """
        Process a chat message through the workflow agent system.
        
        This method provides the same interface as ChatAgentManager.chat()
        but uses the WorkflowChatAgent internally.
        """
        # Ensure agent is built
        if self.workflow_agent is None:
            await self.build_agent(user_input)
        
        # Use workflow agent to process the message
        agent = self._ensure_workflow_agent()
        response = await agent.chat(user_input)
        
        logger.info(f"Workflow agent handled query, response length: {len(response)}")
        return response 