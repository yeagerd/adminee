"""
Event definitions for the LlamaIndex Workflow-based chat agent system.

This module defines all events used in the workflow orchestration, including:
- Base event classes with common functionality
- User interaction events
- Tool execution events
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




class ToolExecutorCompletedEvent(Event):
    """
    Event representing completion of tool execution step.
    
    This event is emitted by handle_tool_execution_request() when all requested tools 
    have been executed. Can be used to trigger follow-up actions in the workflow.
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





class ToolResultsForPlannerEvent(Event):
    """
    Event representing tool execution results that should trigger re-planning.
    
    This event is emitted by handle_tool_execution_request() when route_to_planner=True.
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
    
    This event is emitted by handle_tool_execution_request() when route_to_planner=False.
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





class DraftCreatedEvent(Event):
    """
    Terminal event representing successful draft creation.
    
    This event marks the completion of the workflow when handle_tool_results_for_draft()
    successfully creates a draft from the gathered information.
    """
    
    thread_id: str
    user_id: str
    draft_content: str
    draft_type: str  # "email", "document", "summary", etc.
    source_events: List[str] = Field(default_factory=list)  # IDs of events that contributed
    draft_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 1.0  # 0.0-1.0 confidence in draft quality
    word_count: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v
    
    def is_high_confidence(self) -> bool:
        """Check if the draft was created with high confidence."""
        return self.confidence_score >= 0.8
    
    def get_content_preview(self, max_chars: int = 200) -> str:
        """Get a preview of the draft content."""
        if len(self.draft_content) <= max_chars:
            return self.draft_content
        return self.draft_content[:max_chars] + "..."


class DraftUpdatedEvent(Event):
    """
    Terminal event representing successful draft update/refinement.
    
    This event is emitted when handle_tool_results_for_draft() refines or updates an existing
    draft based on new information or user feedback.
    """
    
    thread_id: str
    user_id: str
    updated_draft_content: str
    original_draft_content: str
    update_reason: str  # Why the draft was updated
    draft_type: str  # "email", "document", "summary", etc.
    source_events: List[str] = Field(default_factory=list)  # IDs of events that triggered update
    update_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 1.0  # 0.0-1.0 confidence in updated draft quality
    word_count: Optional[int] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("thread_id and user_id must be non-empty strings")
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v
    
    def is_high_confidence(self) -> bool:
        """Check if the updated draft was created with high confidence."""
        return self.confidence_score >= 0.8
    
    def get_content_preview(self, max_chars: int = 200) -> str:
        """Get a preview of the updated draft content."""
        if len(self.updated_draft_content) <= max_chars:
            return self.updated_draft_content
        return self.updated_draft_content[:max_chars] + "..."
    
    def get_changes_summary(self) -> str:
        """Get a summary of what changed in the draft."""
        return f"Updated: {self.update_reason}"


class ContextUpdatedEvent(Event):
    """
    Event representing context updates that accumulate across workflow steps.
    
    This event is used to maintain and update shared context as information
    is gathered throughout the workflow execution. Steps can emit this event
    to update the global workflow context.
    """
    
    thread_id: str
    user_id: str
    context_updates: Dict[str, Any]  # New context information to merge
    update_source: str  # Which step/component updated the context
    update_type: str  # "merge", "replace", "append"
    priority: str = "medium"  # "high", "medium", "low"
    context_version: int = 1  # Context version for tracking changes
    parent_event_id: Optional[str] = None  # Event that triggered this update
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    @field_validator('thread_id', 'user_id', 'update_source')
    @classmethod
    def validate_required_strings(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Required string fields must be non-empty")
        return v
    
    @field_validator('update_type')
    @classmethod
    def validate_update_type(cls, v):
        valid_types = ["merge", "replace", "append"]
        if v not in valid_types:
            raise ValueError(f"update_type must be one of: {valid_types}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = ["high", "medium", "low"]
        if v not in valid_priorities:
            raise ValueError(f"priority must be one of: {valid_priorities}")
        return v
    
    def is_high_priority(self) -> bool:
        """Check if this context update is high priority."""
        return self.priority == "high"
    
    def get_context_keys(self) -> List[str]:
        """Get the keys being updated in the context."""
        return list(self.context_updates.keys())
    
    def has_context_key(self, key: str) -> bool:
        """Check if a specific context key is being updated."""
        return key in self.context_updates
    
    def merge_with_context(self, existing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge this update with existing context based on update_type."""
        if self.update_type == "replace":
            return {**existing_context, **self.context_updates}
        elif self.update_type == "merge":
            merged = existing_context.copy()
            for key, value in self.context_updates.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
            return merged
        elif self.update_type == "append":
            merged = existing_context.copy()
            for key, value in self.context_updates.items():
                if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = merged[key] + value
                else:
                    merged[key] = value
            return merged
        return existing_context


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
    'ToolResultsForDrafterEvent',
    'ClarificationReplanRequestedEvent',
    'ClarificationPlannerUnblockedEvent',
    'ClarificationDraftUnblockedEvent',
    'DraftCreatedEvent',
    'DraftUpdatedEvent',
    'ContextUpdatedEvent'
] 