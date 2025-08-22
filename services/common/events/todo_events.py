"""
Todo event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent


class TodoData(BaseModel):
    """Todo data structure."""

    id: str = Field(..., description="Unique todo ID")
    title: str = Field(..., description="Todo title")
    description: Optional[str] = Field(None, description="Todo description")
    status: str = Field(
        default="pending",
        description="Todo status (pending, in_progress, completed, cancelled)",
    )
    priority: str = Field(
        default="medium", description="Todo priority (low, medium, high, urgent)"
    )
    due_date: Optional[datetime] = Field(None, description="Due date for the todo")
    completed_date: Optional[datetime] = Field(
        None, description="When the todo was completed"
    )
    assignee_email: Optional[str] = Field(None, description="Assignee's email")
    creator_email: str = Field(..., description="Creator's email")
    tags: List[str] = Field(default_factory=list, description="Todo tags")
    parent_todo_id: Optional[str] = Field(
        None, description="Parent todo ID for subtasks"
    )
    subtask_ids: List[str] = Field(
        default_factory=list, description="List of subtask IDs"
    )
    provider: str = Field(..., description="Todo provider (google, microsoft, etc.)")
    provider_todo_id: str = Field(..., description="Provider's internal todo ID")
    list_id: Optional[str] = Field(None, description="Todo list ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional todo metadata"
    )


class TodoEvent(BaseEvent):
    """Event for todo operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the todo operation")
    todo: TodoData = Field(..., description="Todo data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the todo was last updated")
    sync_timestamp: datetime = Field(
        ..., description="When the data was last synced from provider"
    )
    provider: str = Field(..., description="Todo provider (google, microsoft, etc.)")
    list_id: Optional[str] = Field(None, description="Todo list ID")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class TodoListData(BaseModel):
    """Todo list data structure."""

    id: str = Field(..., description="Unique todo list ID")
    name: str = Field(..., description="List name")
    description: Optional[str] = Field(None, description="List description")
    color: Optional[str] = Field(None, description="List color")
    is_default: bool = Field(
        default=False, description="Whether this is the default list"
    )
    provider: str = Field(..., description="Todo provider (google, microsoft, etc.)")
    provider_list_id: str = Field(..., description="Provider's internal list ID")
    owner_email: str = Field(..., description="List owner's email")
    shared_with: List[str] = Field(
        default_factory=list, description="Emails of users the list is shared with"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional list metadata"
    )


class TodoListEvent(BaseEvent):
    """Event for todo list operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the todo list operation")
    todo_list: TodoListData = Field(..., description="Todo list data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(
        None, description="Batch identifier for batch operations"
    )
    last_updated: datetime = Field(..., description="When the list was last updated")
    sync_timestamp: datetime = Field(
        ..., description="When the data was last synced from provider"
    )
    provider: str = Field(..., description="Todo provider (google, microsoft, etc.)")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"
