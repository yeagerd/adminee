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


# Export base classes for use in concrete event implementations
__all__ = [
    'BaseWorkflowEvent',
    'WorkflowMetadata', 
    'ExecutionPlan',
    'ClarificationRequest'
] 