"""
Chat service API endpoints.

This module implements the REST API for the chat service and demonstrates
the conversion pattern between database models and API response models.

Architectural Pattern - Database to API Model Conversion:
This module shows how database models (Thread, Message) are converted to
API response models (ThreadResponse, MessageResponse) to maintain clean
separation of concerns.

Key Conversion Examples:
1. Thread (DB) -> ThreadResponse (API):
   - int ID -> string ID for JSON compatibility
   - datetime -> string for JSON serialization
   - Exclude SQLAlchemy relationships

2. Message (DB) -> MessageResponse (API):
   - int ID -> string ID for JSON compatibility
   - Add computed fields (llm_generated)
   - datetime -> string for JSON serialization
   - Exclude SQLAlchemy relationships

This pattern ensures:
- Type safety in database operations
- JSON serialization compatibility in API responses
- Independent evolution of database schema and API contracts
- Clean separation between data persistence and API concerns
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from services.chat.workflow_manager import WorkflowChatAgentManager
from services.chat.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from services.chat.models import MessageResponse as PydanticMessage
from services.chat.models import (
    ThreadResponse,
)
from services.chat.settings import get_settings

router = APIRouter()

# In-memory feedback storage
FEEDBACKS: List[FeedbackRequest] = []


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint using llama_manager ChatAgentManager.

    Demonstrates database model to API model conversion pattern.
    """
    from typing import cast

    from services.chat import history_manager

    user_id = request.user_id
    thread_id = request.thread_id
    user_input = request.message

    # Create or get thread (returns database Thread model)
    thread: Optional[history_manager.Thread]
    if not thread_id:
        # Always create a new thread if no thread_id is provided
        thread = await history_manager.create_thread(user_id=user_id)
    else:
        # Fetch the existing thread
        try:
            thread_id_int = int(thread_id)
            thread = await history_manager.get_thread(thread_id=thread_id_int)
            if thread is None:
                raise HTTPException(status_code=404, detail="Thread not found")
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400, detail="Invalid thread_id format. Must be an integer."
            ) from e

    # At this point, thread is guaranteed to be not None
    thread = cast(history_manager.Thread, thread)

    # Initialize the workflow agent with LLM from LLMManager
    agent = WorkflowChatAgentManager(
        thread_id=int(thread.id),
        user_id=user_id,
        tools=[],
        subagents=[],
        # These will use settings
        llm_model=get_settings().llm_model,
        llm_provider=get_settings().llm_provider,
    )
    # Actually run the chat and get the agent's response
    agent_response = await agent.chat(user_input)

    # CONVERSION PATTERN: Create API response model from data
    # Note: This creates MessageResponse (API model) directly rather than
    # converting from Message (database model) since this is a new response
    pydantic_messages = [
        PydanticMessage(
            message_id="1",  # Simple counter since we're not fetching from DB
            thread_id=str(thread.id),  # Convert int to string for JSON
            user_id="assistant",  # Mark as assistant response
            llm_generated=True,  # Computed field not in database model
            content=agent_response,
            created_at="",  # Not needed for this simple response
        )
    ]
    return ChatResponse(
        thread_id=str(agent.thread_id), messages=pydantic_messages, draft=None
    )


@router.get("/threads", response_model=List[ThreadResponse])
async def list_threads(user_id: str) -> List[ThreadResponse]:
    """
    List threads for a given user using history_manager.

    CONVERSION PATTERN EXAMPLE: Thread (database) -> ThreadResponse (API)
    This function demonstrates the standard pattern for converting database
    models to API response models.
    """
    from services.chat import history_manager

    # Get database models (Thread objects with int IDs, datetime objects, relationships)
    threads = await history_manager.list_threads(user_id)

    # CONVERSION: Database Thread models -> API ThreadResponse models
    return [
        ThreadResponse(
            thread_id=str(t.id),  # CONVERT: int -> str for JSON compatibility
            user_id=t.user_id,  # DIRECT: string field passes through
            created_at=str(t.created_at),  # CONVERT: datetime -> str for JSON
            updated_at=str(t.updated_at),  # CONVERT: datetime -> str for JSON
            # NOTE: Relationships (messages, drafts) are excluded from API model
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}/history", response_model=ChatResponse)
async def thread_history(thread_id: str) -> ChatResponse:
    """
    Get chat history for a given thread using history_manager.

    CONVERSION PATTERN EXAMPLE: Message (database) -> MessageResponse (API)
    This function demonstrates the standard pattern for converting database
    models to API response models with computed fields.
    """
    from services.chat import history_manager
    from services.chat.models import MessageResponse

    # Get database models (Message objects with int IDs, datetime objects, relationships)
    messages = await history_manager.get_thread_history(int(thread_id), limit=100)

    # CONVERSION: Database Message models -> API MessageResponse models
    chat_messages = [
        MessageResponse(
            message_id=str(i + 1),  # GENERATE: Create string ID for API
            thread_id=str(thread_id),  # CONVERT: int -> str for JSON compatibility
            user_id=(
                str(m.user_id) if m.user_id is not None else ""
            ),  # CONVERT: handle nulls
            # COMPUTED FIELD: Add business logic not present in database model
            llm_generated=(m.user_id != messages[0].user_id if messages else False),
            content=(
                str(m.content) if m.content is not None else ""
            ),  # CONVERT: handle nulls
            created_at=str(m.created_at),  # CONVERT: datetime -> str for JSON
            # NOTE: Relationship (thread) is excluded from API model
        )
        for i, m in enumerate(reversed(messages))
    ]
    return ChatResponse(thread_id=str(thread_id), messages=chat_messages, draft=None)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback_endpoint(request: FeedbackRequest) -> FeedbackResponse:
    """
    Receive user feedback for a message.
    """
    FEEDBACKS.append(request)
    return FeedbackResponse(status="success")
