"""
API request and response models for chat service.

This module defines Pydantic models used for API serialization and validation.
It follows a clear architectural pattern where API models are separate from
database models to ensure proper separation of concerns.

Database Models vs. API Response Models:
- Database models (Thread, Message, Draft) use SQLModel for ORM functionality
- API response models (ThreadResponse, MessageResponse) use Pydantic for serialization
- This separation allows for type safety, field transformation, and independent evolution

Key Design Decisions:
- API models use string types for JSON serialization compatibility
- API models can add computed fields not present in database (e.g., llm_generated)
- API models exclude internal database relationships and sensitive data
- API models control exactly what data is exposed to clients
- API models can evolve independently from database schema

Conversion Pattern:
- Database models are converted to API models in the API layer
- This conversion allows for field transformation, computed fields, and data filtering
- See api.py for examples of this conversion pattern
"""

from typing import List, Optional, Union

from pydantic import BaseModel


class DraftEmail(BaseModel):
    """Draft email data structure."""

    type: str = "email"
    to: Optional[str] = None
    cc: Optional[str] = None
    bcc: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    thread_id: str
    created_at: str
    updated_at: Optional[str] = None


class DraftCalendarEvent(BaseModel):
    """Draft calendar event data structure."""

    type: str = "calendar_event"
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    attendees: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    thread_id: str
    created_at: str
    updated_at: Optional[str] = None


class DraftCalendarChange(BaseModel):
    """Draft calendar change data structure."""

    type: str = "calendar_change"
    event_id: Optional[str] = None
    change_type: Optional[str] = None
    new_title: Optional[str] = None
    new_start_time: Optional[str] = None
    new_end_time: Optional[str] = None
    new_attendees: Optional[str] = None
    new_location: Optional[str] = None
    new_description: Optional[str] = None
    thread_id: str
    created_at: str
    updated_at: Optional[str] = None


# Union type for all draft types
DraftData = Union[DraftEmail, DraftCalendarEvent, DraftCalendarChange]


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.

    Represents a user's chat message request with optional thread context.
    User ID is provided via X-User-Id header from the gateway.
    """

    thread_id: Optional[str] = None  # String for JSON compatibility
    message: str
    user_timezone: Optional[str] = (
        None  # Will be looked up from user preferences if not provided
    )


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.

    Contains the complete chat response including thread context and messages.
    Uses MessageResponse models for consistent API serialization.
    """

    thread_id: str  # String for JSON compatibility
    messages: List["MessageResponse"]
    drafts: Optional[List[DraftData]] = None  # Structured draft data


class ThreadResponse(BaseModel):
    """
    API response model for chat threads.

    This is the API/serialization representation of a chat thread, separate from
    the database Thread model to maintain clean separation of concerns.

    Note: This model is separate from Thread (database model) to maintain
    clean separation between data persistence and API contracts.

    API Design:
    - Uses string types for JSON serialization compatibility
    - Excludes internal database relationships (messages, drafts)
    - Excludes sensitive or internal fields (e.g., database constraints)
    - Provides stable API contract independent of database schema

    Database Conversion:
    - Created by converting Thread database model in API layer
    - ID fields converted from int to string for JSON compatibility
    - Datetime fields converted to string for JSON serialization
    - Relationships excluded for clean API response

    Example conversion from Thread database model:
        ThreadResponse(
            thread_id=str(thread.id),           # int -> str
            user_id=thread.user_id,
            created_at=str(thread.created_at),  # datetime -> str
            updated_at=str(thread.updated_at),  # datetime -> str
        )
    """

    thread_id: str  # Converted from int ID in database model
    user_id: str
    created_at: str  # Converted from datetime in database model
    updated_at: str  # Converted from datetime in database model


class MessageResponse(BaseModel):
    """
    API response model for chat messages.

    This is the API/serialization representation of a chat message, separate from
    the database Message model to maintain clean separation of concerns.

    Note: This model is separate from Message (database model) to maintain
    clean separation between data persistence and API contracts.

    API Design:
    - Uses string types for JSON serialization compatibility
    - Adds computed fields not present in database (llm_generated)
    - Excludes internal database relationships (thread)
    - Provides stable API contract independent of database schema
    - Uses descriptive field names (message_id vs id)

    Database Conversion:
    - Created by converting Message database model in API layer
    - ID fields converted from int to string for JSON compatibility
    - Datetime fields converted to string for JSON serialization
    - Computed fields added based on business logic
    - Relationships excluded for clean API response

    Example conversion from Message database model:
        MessageResponse(
            message_id=str(message.id),         # int -> str, renamed
            thread_id=str(message.thread_id),   # int -> str
            user_id=message.user_id,
            llm_generated=(message.user_id != user_id),  # computed field
            content=message.content,
            created_at=str(message.created_at), # datetime -> str
        )
    """

    message_id: str  # Converted from int ID in database model, renamed for clarity
    thread_id: str  # Converted from int foreign key in database model
    user_id: str
    llm_generated: bool = False  # Computed field not present in database model
    content: str
    created_at: str  # Converted from datetime in database model


class FeedbackRequest(BaseModel):
    """
    Request model for user feedback on messages.

    Allows users to provide thumbs up/down feedback on AI responses.
    """

    user_id: str
    thread_id: str  # String for JSON compatibility
    message_id: str  # String for JSON compatibility
    feedback: str  # 'up' or 'down'


class FeedbackResponse(BaseModel):
    """
    Response model for feedback submission.

    Simple acknowledgment response for feedback requests.
    """

    status: str
    detail: Optional[str] = None
