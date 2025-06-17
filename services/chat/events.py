"""
Event definitions for the LlamaIndex Workflow-based chat agent system.

This module defines all events used in the workflow orchestration, including:
- Base event classes with common functionality
- User interaction events
- Tool execution events
- Clarification events
- Draft lifecycle events
- Streaming status events

Events are used to communicate between workflow steps and maintain
state throughout the agent execution process.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from llama_index.core.workflow import Event
from pydantic import BaseModel, Field, field_validator


class WorkflowMetadata(BaseModel):
    """Metadata container for workflow events."""
    
    confidence: Optional[float] = None
    priority: Optional[str] = None  # "high", "medium", "low"
    retry_count: int = 0
    parent_event_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class ExecutionPlan(BaseModel):
    """Represents an execution plan with task groups and strategy."""
    
    goal: str
    confidence: float = Field(ge=0.0, le=1.0)
    execution_strategy: str  # "parallel_preferred" or "sequential_required"
    task_groups: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    estimated_duration: Optional[str] = None
    
    def add_task_group(self, tasks: List[str], can_run_parallel: bool = True, 
                      estimated_duration: Optional[str] = None):
        """Add a task group to the execution plan."""
        self.task_groups.append({
            "can_run_parallel": can_run_parallel,
            "tasks": tasks,
            "estimated_duration": estimated_duration
        })


class ClarificationRequest(BaseModel):
    """Represents a clarification request to the user."""
    
    question: str
    blocking: bool = True  # Whether this blocks execution
    confidence_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    context: Dict[str, Any] = Field(default_factory=dict)
    suggested_answers: Optional[List[str]] = None
    timeout_seconds: Optional[int] = None


class UserInputEvent(Event):
    """
    Event representing user input to the workflow system.
    
    Contains the user's message along with metadata about the interaction.
    This is typically the first event in the workflow chain.
    """
    
    thread_id: str
    user_id: str
    message: str
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Message must be a non-empty string")
        return v.strip()


class ToolExecutionRequestedEvent(Event):
    """
    Event that the planner emits to request tool execution.
    
    This is the trigger event that routes from Planner → ToolExecutor.
    Contains the tools to execute and their parameters.
    """
    
    thread_id: str
    user_id: str
    tools_to_execute: List[Dict[str, Any]]  # List of {tool_name, inputs, execution_group_id}
    execution_strategy: str  # "parallel" or "sequential"
    parent_plan_event_id: str
    priority: str = "medium"  # "high", "medium", "low"
    timeout_seconds: Optional[int] = None
    route_to_planner: bool = False  # Whether results should route to planner (True) or drafter (False)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    @field_validator('tools_to_execute')
    @classmethod
    def validate_tools(cls, v):
        if not v or not isinstance(v, list):
            raise ValueError("tools_to_execute must be a non-empty list")
        for tool in v:
            if not isinstance(tool, dict) or 'tool_name' not in tool:
                raise ValueError("Each tool must be a dict with 'tool_name' key")
        return v
    
    def get_parallel_tools(self) -> List[Dict[str, Any]]:
        """Get tools that can be executed in parallel."""
        if self.execution_strategy == "parallel":
            return self.tools_to_execute
        return []
    
    def should_execute_parallel(self) -> bool:
        """Check if tools should be executed in parallel."""
        return self.execution_strategy == "parallel"


class ClarificationRequestedEvent(Event):
    """
    Event that the planner emits to request user clarification.
    
    This is the trigger event that routes from Planner → Clarifier.
    Contains the clarification questions and context.
    """
    
    thread_id: str
    user_id: str
    clarification_requests: List[ClarificationRequest]
    parent_plan_event_id: str
    workflow_context: Dict[str, Any] = Field(default_factory=dict)
    can_proceed_without: bool = False  # Can workflow continue without clarification
    blocks_planning: bool = True  # Whether this clarification blocks planning vs drafting
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    @field_validator('clarification_requests')
    @classmethod
    def validate_requests(cls, v):
        if not v or not isinstance(v, list):
            raise ValueError("clarification_requests must be a non-empty list")
        return v
    
    def get_blocking_requests(self) -> List[ClarificationRequest]:
        """Get clarification requests that block execution."""
        return [req for req in self.clarification_requests if req.blocking]
    
    def has_blocking_requests(self) -> bool:
        """Check if any clarification requests block execution."""
        return len(self.get_blocking_requests()) > 0
    
    def get_all_questions(self) -> List[str]:
        """Get all clarification questions."""
        return [req.question for req in self.clarification_requests]


class ToolExecutorCompletedEvent(Event):
    """
    Event representing completion of tool execution step.
    
    This event is emitted by ToolExecutorStep when all requested tools 
    have been executed. Used with LlamaIndex collect pattern to trigger
    DraftBuilderStep when both tool execution and clarification are complete.
    """
    
    thread_id: str
    user_id: str
    parent_request_event_id: str  # ID of the ToolExecutionRequestedEvent
    tool_results: Dict[str, Any]  # Results from all executed tools
    execution_success: bool
    error_messages: List[str] = Field(default_factory=list)
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    def has_errors(self) -> bool:
        """Check if tool execution had any errors."""
        return not self.execution_success or len(self.error_messages) > 0
    
    def get_successful_results(self) -> Dict[str, Any]:
        """Get results from successfully executed tools."""
        if self.execution_success:
            return self.tool_results
        return {}


class ClarifierCompletedEvent(Event):
    """
    Event representing completion of clarification step.
    
    This event is emitted by ClarifierStep when user clarifications have
    been processed. Used with LlamaIndex collect pattern to trigger
    DraftBuilderStep when both tool execution and clarification are complete.
    """
    
    thread_id: str
    user_id: str
    parent_request_event_id: str  # ID of the ClarificationRequestedEvent
    clarification_answers: Dict[str, str]  # Question -> Answer mapping
    resolution_success: bool
    unanswered_questions: List[str] = Field(default_factory=list)
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    def has_unanswered_questions(self) -> bool:
        """Check if there are still unanswered clarification questions."""
        return len(self.unanswered_questions) > 0
    
    def is_complete(self) -> bool:
        """Check if clarification process is complete."""
        return self.resolution_success and not self.has_unanswered_questions()
    
    def get_answer(self, question: str) -> Optional[str]:
        """Get the answer for a specific question."""
        return self.clarification_answers.get(question)


class ToolResultsForPlannerEvent(Event):
    """
    Event representing tool execution results that should trigger re-planning.
    
    This event is emitted by ToolExecutorStep when route_to_planner=True.
    Contains tool results that may change the planning strategy or require
    plan updates based on new information discovered.
    """
    
    thread_id: str
    user_id: str
    parent_request_event_id: str  # ID of the ToolExecutionRequestedEvent
    tool_results: Dict[str, Any]  # Results from all executed tools
    execution_success: bool
    error_messages: List[str] = Field(default_factory=list)
    planning_insights: Dict[str, Any] = Field(default_factory=dict)  # Key insights for re-planning
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    def has_errors(self) -> bool:
        """Check if tool execution had any errors."""
        return not self.execution_success or len(self.error_messages) > 0
    
    def get_successful_results(self) -> Dict[str, Any]:
        """Get results from successfully executed tools."""
        if self.execution_success:
            return self.tool_results
        return {}
    
    def requires_replanning(self) -> bool:
        """Check if results indicate need for re-planning."""
        return self.execution_success and bool(self.planning_insights)


class ToolResultsForDrafterEvent(Event):
    """
    Event representing tool execution results ready for draft creation.
    
    This event is emitted by ToolExecutorStep when route_to_planner=False.
    Contains tool results that are ready to be used directly for drafting
    without requiring plan changes.
    """
    
    thread_id: str
    user_id: str
    parent_request_event_id: str  # ID of the ToolExecutionRequestedEvent
    tool_results: Dict[str, Any]  # Results from all executed tools
    execution_success: bool
    error_messages: List[str] = Field(default_factory=list)
    draft_context: Dict[str, Any] = Field(default_factory=dict)  # Context for draft creation
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    def has_errors(self) -> bool:
        """Check if tool execution had any errors."""
        return not self.execution_success or len(self.error_messages) > 0
    
    def get_successful_results(self) -> Dict[str, Any]:
        """Get results from successfully executed tools."""
        if self.execution_success:
            return self.tool_results
        return {}
    
    def is_ready_for_draft(self) -> bool:
        """Check if results are ready for draft creation."""
        return self.execution_success and bool(self.tool_results)


# Export event classes and supporting models
__all__ = [
    'WorkflowMetadata', 
    'ExecutionPlan',
    'ClarificationRequest',
    'UserInputEvent',
    'ToolExecutionRequestedEvent',
    'ClarificationRequestedEvent',
    'ToolExecutorCompletedEvent',
    'ClarifierCompletedEvent',
    'ToolResultsForPlannerEvent',
    'ToolResultsForDrafterEvent'
] 