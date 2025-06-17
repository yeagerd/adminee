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

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from llama_index.core.workflow import Event
from pydantic import BaseModel, Field, validator


class BaseWorkflowEvent(Event, ABC):
    """
    Base class for all workflow events with common functionality.
    
    Provides:
    - Event ID generation and tracking
    - Timestamp management
    - Serialization/deserialization
    - Event validation
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    thread_id: str
    user_id: str
    
    def __init__(self, **data):
        super().__init__(**data)
    
    @validator('thread_id', 'user_id')
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            **self._get_event_data()
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @abstractmethod
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data for serialization."""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseWorkflowEvent':
        """Create event from dictionary."""
        # Convert timestamp back to datetime if it's a string
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(event_id={self.event_id}, thread_id={self.thread_id})"


class WorkflowMetadata(BaseModel):
    """Metadata container for workflow events."""
    
    confidence: Optional[float] = None
    priority: Optional[str] = None  # "high", "medium", "low"
    retry_count: int = 0
    parent_event_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('confidence')
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


class UserInputEvent(BaseWorkflowEvent):
    """
    Event representing user input to the workflow system.
    
    Contains the user's message along with metadata about the interaction.
    This is typically the first event in the workflow chain.
    """
    
    message: str
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Message must be a non-empty string")
        return v.strip()
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get UserInputEvent-specific data for serialization."""
        return {
            "message": self.message,
            "metadata": self.metadata.dict(),
            "conversation_history": self.conversation_history,
            "user_preferences": self.user_preferences
        }


class PlanGeneratedEvent(BaseWorkflowEvent):
    """
    Event representing a generated execution plan from the Planner step.
    
    Contains the structured plan with task groups, confidence levels,
    and execution strategy determined by the planner.
    """
    
    execution_plan: ExecutionPlan
    original_request: str
    clarifications_needed: List[ClarificationRequest] = Field(default_factory=list)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get PlanGeneratedEvent-specific data for serialization."""
        return {
            "execution_plan": self.execution_plan.dict(),
            "original_request": self.original_request,
            "clarifications_needed": [req.dict() for req in self.clarifications_needed],
            "metadata": self.metadata.dict()
        }
    
    def requires_clarification(self) -> bool:
        """Check if this plan requires user clarification before execution."""
        return len(self.clarifications_needed) > 0
    
    def get_blocking_clarifications(self) -> List[ClarificationRequest]:
        """Get clarifications that block execution."""
        return [req for req in self.clarifications_needed if req.blocking]
    
    def get_non_blocking_clarifications(self) -> List[ClarificationRequest]:
        """Get clarifications that don't block execution."""
        return [req for req in self.clarifications_needed if not req.blocking]


class ToolExecutionStartedEvent(BaseWorkflowEvent):
    """
    Event representing the start of tool execution.
    
    Tracks when tools begin executing, including parallel execution
    coordination and progress monitoring.
    """
    
    tool_name: str
    tool_inputs: Dict[str, Any]
    execution_group_id: str  # For tracking parallel executions
    parent_plan_event_id: str
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @validator('tool_name')
    def validate_tool_name(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Tool name must be a non-empty string")
        return v
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get ToolExecutionStartedEvent-specific data for serialization."""
        return {
            "tool_name": self.tool_name,
            "tool_inputs": self.tool_inputs,
            "execution_group_id": self.execution_group_id,
            "parent_plan_event_id": self.parent_plan_event_id,
            "metadata": self.metadata.dict()
        }


class ToolExecutionCompletedEvent(BaseWorkflowEvent):
    """
    Event representing the completion of tool execution.
    
    Contains results, errors, and execution metrics for completed tools.
    """
    
    tool_name: str
    tool_inputs: Dict[str, Any]
    tool_outputs: Dict[str, Any]
    execution_group_id: str
    parent_plan_event_id: str
    execution_time_seconds: float
    success: bool
    error_message: Optional[str] = None
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @validator('tool_name')
    def validate_tool_name(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Tool name must be a non-empty string")
        return v
    
    @validator('execution_time_seconds')
    def validate_execution_time(cls, v):
        if v < 0:
            raise ValueError("Execution time must be non-negative")
        return v
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get ToolExecutionCompletedEvent-specific data for serialization."""
        return {
            "tool_name": self.tool_name,
            "tool_inputs": self.tool_inputs,
            "tool_outputs": self.tool_outputs,
            "execution_group_id": self.execution_group_id,
            "parent_plan_event_id": self.parent_plan_event_id,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata.dict()
        }
    
    def has_error(self) -> bool:
        """Check if tool execution resulted in an error."""
        return not self.success or self.error_message is not None


class ClarificationNeededEvent(BaseWorkflowEvent):
    """
    Event representing the need for user clarification.
    
    Routes questions to the user interface and tracks the clarification
    context for proper answer routing back to the workflow.
    """
    
    clarification_request: ClarificationRequest
    parent_plan_event_id: str
    workflow_state: Dict[str, Any] = Field(default_factory=dict)  # Current workflow state
    blocking_execution: bool = True  # Whether this blocks workflow continuation
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get ClarificationNeededEvent-specific data for serialization."""
        return {
            "clarification_request": self.clarification_request.dict(),
            "parent_plan_event_id": self.parent_plan_event_id,
            "workflow_state": self.workflow_state,
            "blocking_execution": self.blocking_execution,
            "metadata": self.metadata.dict()
        }
    
    def is_blocking(self) -> bool:
        """Check if this clarification blocks workflow execution."""
        return self.blocking_execution and self.clarification_request.blocking
    
    def get_question(self) -> str:
        """Get the clarification question for display."""
        return self.clarification_request.question
    
    def get_suggested_answers(self) -> Optional[List[str]]:
        """Get suggested answers if available."""
        return self.clarification_request.suggested_answers
    
    def has_timeout(self) -> bool:
        """Check if this clarification has a timeout."""
        return self.clarification_request.timeout_seconds is not None


# Export base classes for use in concrete event implementations
__all__ = [
    'BaseWorkflowEvent',
    'WorkflowMetadata', 
    'ExecutionPlan',
    'ClarificationRequest',
    'UserInputEvent',
    'PlanGeneratedEvent',
    'ToolExecutionStartedEvent',
    'ToolExecutionCompletedEvent',
    'ClarificationNeededEvent'
] 