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

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from services.chat import history_manager
from services.chat.agents.workflow_agent import WorkflowAgent
from services.chat.auth import require_chat_auth
from services.chat.history_manager import count_user_drafts
from services.chat.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    MessageResponse,
    ThreadResponse,
    UserDraftListResponse,
    UserDraftRequest,
    UserDraftResponse,
)
from services.chat.service_client import ServiceClient
from services.chat.settings import get_settings
from services.common.http_errors import NotFoundError, ValidationError
from services.common.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# In-memory feedback storage
FEEDBACKS: List[FeedbackRequest] = []


async def get_user_id_from_gateway(request: Request) -> str:
    """
    Extract user ID from gateway headers.

    The chat service only supports requests through the gateway,
    which forwards user identity via X-User-Id header.
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise ValidationError(message="X-User-Id header is required", field="X-User-Id")
    return user_id


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> ChatResponse:
    """
    Chat endpoint using WorkflowAgent multi-agent system.

    Demonstrates database model to API model conversion pattern.
    """
    from typing import cast

    user_id = await get_user_id_from_gateway(request)
    thread_id = chat_request.thread_id
    user_input = chat_request.message
    user_timezone = chat_request.user_timezone

    # Get user timezone from preferences if not provided
    if not user_timezone:
        async with ServiceClient() as service_client:
            preferences = await service_client.get_user_preferences(user_id)
            if preferences and "timezone" in preferences:
                user_timezone = preferences["timezone"]
            else:
                user_timezone = "UTC"  # Default fallback

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
                raise NotFoundError("Thread", thread_id)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                message="Invalid thread_id format. Must be an integer.",
                field="thread_id",
                value=thread_id,
            ) from e

    # At this point, thread is guaranteed to be not None
    thread = cast(history_manager.Thread, thread)

    # Initialize the multi-agent workflow with user timezone
    if thread.id is None:
        raise ValidationError(message="thread.id cannot be None", field="thread.id")
    agent = WorkflowAgent(
        thread_id=int(thread.id),
        user_id=user_id,
        llm_model=get_settings().llm_model,
        llm_provider=get_settings().llm_provider,
        max_tokens=get_settings().max_tokens,
        user_timezone=user_timezone,  # Pass user timezone to agent
    )

    # Build the agent workflow if not already built
    await agent.build_agent(user_input)

    # Actually run the chat and get the agent's response
    agent_response = await agent.chat(user_input)

    # Extract structured draft data
    draft_data = await agent.get_draft_data()

    # Convert draft data to API models
    from services.chat.models import DraftCalendarChange, DraftCalendarEvent, DraftEmail

    structured_drafts = []

    for draft in draft_data:
        draft_type = draft.get("type", "")
        if draft_type == "email":
            structured_drafts.append(DraftEmail(**draft))
        elif draft_type == "calendar_event":
            structured_drafts.append(DraftCalendarEvent(**draft))  # type: ignore[arg-type]
        elif draft_type == "calendar_change":
            structured_drafts.append(DraftCalendarChange(**draft))  # type: ignore[arg-type]

    # CONVERSION PATTERN: Create API response model from data
    # Note: This creates MessageResponse (API model) directly rather than
    # converting from Message (database model) since this is a new response
    pydantic_messages = [
        MessageResponse(
            message_id="1",  # Simple counter since we're not fetching from DB
            thread_id=str(thread.id),  # Convert int to string for JSON
            user_id="assistant",  # Mark as assistant response
            llm_generated=True,  # Computed field not in database model
            content=agent_response,
            created_at="",  # Not needed for this simple response
        )
    ]
    return ChatResponse(
        thread_id=str(agent.thread_id),
        messages=pydantic_messages,
        drafts=structured_drafts if structured_drafts else None,  # type: ignore[arg-type]
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(
    request: Request,
    chat_request: ChatRequest,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> StreamingResponse:
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    This endpoint streams the multi-agent workflow responses in real-time,
    allowing clients to see responses as they're generated.
    """
    from typing import cast

    from services.chat import history_manager

    user_id = await get_user_id_from_gateway(request)
    thread_id = chat_request.thread_id
    user_input = chat_request.message
    user_timezone = chat_request.user_timezone

    # Get user timezone from preferences if not provided
    if not user_timezone:
        async with ServiceClient() as service_client:
            preferences = await service_client.get_user_preferences(user_id)
            if preferences and "timezone" in preferences:
                user_timezone = preferences["timezone"]
            else:
                user_timezone = "UTC"  # Default fallback

    # Create or get thread (returns database Thread model)
    thread: Optional[history_manager.Thread]
    if not thread_id:
        thread = await history_manager.create_thread(user_id=user_id)
    else:
        try:
            thread_id_int = int(thread_id)
            thread = await history_manager.get_thread(thread_id=thread_id_int)
            if thread is None:
                raise NotFoundError("Thread", thread_id)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                message="Invalid thread_id format. Must be an integer.",
                field="thread_id",
                value=thread_id,
            ) from e
    thread = cast(history_manager.Thread, thread)

    async def generate_streaming_response():
        """Generate streaming response using Server-Sent Events format."""
        try:
            # Initialize the multi-agent workflow with user timezone
            if thread.id is None:
                raise ValidationError(
                    message="thread.id cannot be None", field="thread.id"
                )
            agent = WorkflowAgent(
                thread_id=int(thread.id),
                user_id=user_id,
                llm_model=get_settings().llm_model,
                llm_provider=get_settings().llm_provider,
                max_tokens=get_settings().max_tokens,
                user_timezone=user_timezone,  # Pass user timezone to agent
            )

            # Build the agent workflow if not already built
            await agent.build_agent(user_input)

            # Send initial metadata
            yield f"event: metadata\ndata: {json.dumps({'thread_id': str(thread.id), 'user_id': user_id})}\n\n"

            # Stream the workflow responses
            full_response = ""
            async for event in agent.stream_chat(user_input):
                # Convert event to JSON and send as SSE
                event_data = {
                    "type": type(event).__name__,
                    "content": str(event) if hasattr(event, "__str__") else "",
                }

                # Extract delta if available
                delta_value = getattr(event, "delta", None)
                if delta_value:
                    event_data["delta"] = delta_value
                    full_response += delta_value

                yield f"event: chunk\ndata: {json.dumps(event_data)}\n\n"

            # Wait for final response
            try:
                final_response = await agent.stream_chat(user_input).__anext__()
                if not full_response:
                    full_response = str(final_response)
            except StopAsyncIteration:
                pass

            # Send completion event
            completion_data = {
                "thread_id": str(thread.id),
                "full_response": full_response,
                "status": "completed",
            }
            yield f"event: completed\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            # Send error event
            error_data = {"error": str(e), "status": "error"}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        },
    )


@router.get("/threads", response_model=List[ThreadResponse])
async def list_threads(
    user_id: str,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> List[ThreadResponse]:
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
async def thread_history(
    thread_id: str,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> ChatResponse:
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
    return ChatResponse(thread_id=str(thread_id), messages=chat_messages, drafts=None)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback_endpoint(
    request: FeedbackRequest,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> FeedbackResponse:
    """
    Receive user feedback for a message.
    """
    FEEDBACKS.append(request)
    return FeedbackResponse(status="success", detail="Feedback recorded")


# User Draft Endpoints
@router.post("/user-drafts", response_model=UserDraftResponse)
async def create_user_draft_endpoint(
    request: Request,
    draft_request: UserDraftRequest,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> UserDraftResponse:
    """Create a new user draft."""
    user_id = await get_user_id_from_gateway(request)

    # Convert metadata to JSON string
    metadata_json = "{}"
    if draft_request.metadata:
        metadata_json = json.dumps(draft_request.metadata)

    # Convert thread_id to int if provided
    thread_id_int = None
    if draft_request.thread_id:
        try:
            thread_id_int = int(draft_request.thread_id)
        except (ValueError, TypeError):
            raise ValidationError(
                message="Invalid thread_id format. Must be an integer.",
                field="thread_id",
                value=draft_request.thread_id,
            )

    # Create the draft
    draft = await history_manager.create_user_draft(
        user_id=user_id,
        draft_type=draft_request.type,
        content=draft_request.content,
        metadata=metadata_json,
        thread_id=thread_id_int,
    )

    # Convert to API response model
    return UserDraftResponse(
        id=str(draft.id),
        user_id=draft.user_id,
        type=draft.type,
        content=draft.content,
        metadata=json.loads(draft.draft_metadata),
        status=draft.status,
        thread_id=str(draft.thread_id) if draft.thread_id else None,
        created_at=str(draft.created_at),
        updated_at=str(draft.updated_at),
    )


@router.get("/user-drafts", response_model=UserDraftListResponse)
async def list_user_drafts_endpoint(
    request: Request,
    draft_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> UserDraftListResponse:
    """List user drafts with optional filtering."""
    user_id = await get_user_id_from_gateway(request)

    # Get drafts
    drafts = await history_manager.list_user_drafts(
        user_id=user_id,
        draft_type=draft_type,
        status=status,
        limit=limit + 1,  # Get one extra to check if there are more
        offset=offset,
    )

    # Get total count for pagination
    total_count = await count_user_drafts(
        user_id=user_id,
        draft_type=draft_type,
        status=status,
    )

    # Check if there are more drafts
    has_more = len(drafts) > limit
    if has_more:
        drafts = drafts[:-1]  # Remove the extra draft

    # Convert to API response models
    draft_responses = []
    for draft in drafts:
        draft_responses.append(
            UserDraftResponse(
                id=str(draft.id),
                user_id=draft.user_id,
                type=draft.type,
                content=draft.content,
                metadata=json.loads(draft.draft_metadata),
                status=draft.status,
                thread_id=str(draft.thread_id) if draft.thread_id else None,
                created_at=str(draft.created_at),
                updated_at=str(draft.updated_at),
            )
        )

    return UserDraftListResponse(
        drafts=draft_responses, total_count=total_count, has_more=has_more
    )


@router.get("/user-drafts/{draft_id}", response_model=UserDraftResponse)
async def get_user_draft_endpoint(
    request: Request,
    draft_id: str,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> UserDraftResponse:
    """Get a specific user draft."""
    user_id = await get_user_id_from_gateway(request)

    try:
        draft_id_int = int(draft_id)
    except (ValueError, TypeError):
        raise ValidationError(
            message="Invalid draft_id format. Must be an integer.",
            field="draft_id",
            value=draft_id,
        )

    draft = await history_manager.get_user_draft(draft_id_int)
    if not draft:
        raise NotFoundError("UserDraft", draft_id)

    # Check if the draft belongs to the user
    if draft.user_id != user_id:
        raise ValidationError(
            message="Access denied. Draft does not belong to user.",
            field="draft_id",
            value=draft_id,
        )

    # Convert to API response model
    return UserDraftResponse(
        id=str(draft.id),
        user_id=draft.user_id,
        type=draft.type,
        content=draft.content,
        metadata=json.loads(draft.draft_metadata),
        status=draft.status,
        thread_id=str(draft.thread_id) if draft.thread_id else None,
        created_at=str(draft.created_at),
        updated_at=str(draft.updated_at),
    )


@router.put("/user-drafts/{draft_id}", response_model=UserDraftResponse)
async def update_user_draft_endpoint(
    request: Request,
    draft_id: str,
    draft_request: UserDraftRequest,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
) -> UserDraftResponse:
    """Update a user draft."""
    user_id = await get_user_id_from_gateway(request)

    try:
        draft_id_int = int(draft_id)
    except (ValueError, TypeError):
        raise ValidationError(
            message="Invalid draft_id format. Must be an integer.",
            field="draft_id",
            value=draft_id,
        )

    # Get the existing draft
    existing_draft = await history_manager.get_user_draft(draft_id_int)
    if not existing_draft:
        raise NotFoundError("UserDraft", draft_id)

    # Check if the draft belongs to the user
    if existing_draft.user_id != user_id:
        raise ValidationError(
            message="Access denied. Draft does not belong to user.",
            field="draft_id",
            value=draft_id,
        )

    # Convert metadata to JSON string
    metadata_json = "{}"
    if draft_request.metadata:
        metadata_json = json.dumps(draft_request.metadata)

    # Update the draft
    updated_draft = await history_manager.update_user_draft(
        draft_id_int,
        content=draft_request.content,
        metadata=metadata_json,
        status="draft",  # Keep as draft when updating
    )

    if not updated_draft:
        raise NotFoundError("UserDraft", draft_id)

    # Convert to API response model
    return UserDraftResponse(
        id=str(updated_draft.id),
        user_id=updated_draft.user_id,
        type=updated_draft.type,
        content=updated_draft.content,
        metadata=json.loads(updated_draft.draft_metadata),
        status=updated_draft.status,
        thread_id=str(updated_draft.thread_id) if updated_draft.thread_id else None,
        created_at=str(updated_draft.created_at),
        updated_at=str(updated_draft.updated_at),
    )


@router.delete("/user-drafts/{draft_id}")
async def delete_user_draft_endpoint(
    request: Request,
    draft_id: str,
    client_name: str = Depends(require_chat_auth(allowed_clients=["frontend"])),
):
    """Delete a user draft."""
    user_id = await get_user_id_from_gateway(request)

    try:
        draft_id_int = int(draft_id)
    except (ValueError, TypeError):
        raise ValidationError(
            message="Invalid draft_id format. Must be an integer.",
            field="draft_id",
            value=draft_id,
        )

    # Get the existing draft to check ownership
    existing_draft = await history_manager.get_user_draft(draft_id_int)
    if not existing_draft:
        raise NotFoundError("UserDraft", draft_id)

    # Check if the draft belongs to the user
    if existing_draft.user_id != user_id:
        raise ValidationError(
            message="Access denied. Draft does not belong to user.",
            field="draft_id",
            value=draft_id,
        )

    # Delete the draft
    success = await history_manager.delete_user_draft(draft_id_int)
    if not success:
        raise NotFoundError("UserDraft", draft_id)

    return {"status": "success", "message": "Draft deleted successfully"}
