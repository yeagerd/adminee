"""
Chat service API endpoints.

All user-facing endpoints extract user from the X-User-Id header (set by the gateway).
No user_id is accepted in the path or query for user-facing endpoints.
Internal/service endpoints, if any, should be under /internal and require API key auth.
"""

import json
import uuid
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from services.chat import history_manager
from services.chat.agents.workflow_agent import WorkflowAgent
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


# Feedback data class for storing feedback records
class Feedback(BaseModel):
    """
    Data class for storing feedback records.
    Mirrors the structure of FeedbackRequest for consistency.
    """

    thread_id: str
    message_id: str
    feedback: str
    user_id: str  # Added during feedback processing


# In-memory feedback storage
FEEDBACKS: List[Feedback] = []


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


@router.post("/completions", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
) -> ChatResponse:
    """
    Chat endpoint using WorkflowAgent multi-agent system.

    Demonstrates database model to API model conversion pattern.
    """
    from typing import cast

    user_id = await get_user_id_from_gateway(request)
    thread_id = chat_request.thread_id
    user_input = chat_request.message
    user_timezone = chat_request.effective_timezone  # Use property
    # user_context = chat_request.user_context  # For future use

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

    # Convert draft data to API models, including the database id
    from services.chat.models import DraftCalendarChange, DraftCalendarEvent, DraftEmail

    structured_drafts = []

    for draft in draft_data:
        draft_type = draft.get("type", "")
        # Determine the content field based on draft type
        if draft_type == "email":
            content = draft.get("body", "")
        elif draft_type == "calendar_event":
            content = draft.get("description", "")
        elif draft_type == "calendar_change":
            content = draft.get("new_description", "")
        else:
            content = draft.get("content", "")

        # Persist the draft as a UserDraft
        user_draft = await history_manager.create_user_draft(
            user_id=user_id,
            draft_type=draft_type,
            content=content,
            metadata=json.dumps(draft.get("metadata", {})),
            thread_id=int(thread.id),
        )
        draft_id = (
            str(user_draft.id) if user_draft and user_draft.id is not None else None
        )
        draft_with_id = dict(draft)
        draft_with_id["id"] = draft_id

        if draft_type == "email":
            structured_drafts.append(DraftEmail(**draft_with_id))
        elif draft_type == "calendar_event":
            structured_drafts.append(DraftCalendarEvent(**draft_with_id))  # type: ignore[arg-type]
        elif draft_type == "calendar_change":
            structured_drafts.append(DraftCalendarChange(**draft_with_id))  # type: ignore[arg-type]

    # CONVERSION PATTERN: Create API response model from data
    # Note: This creates MessageResponse (API model) directly rather than
    # converting from Message (database model) since this is a new response
    pydantic_messages = [
        MessageResponse(
            message_id=str(uuid.uuid4()),  # Generate a unique ID for each message
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


@router.post("/completions/stream")
async def chat_stream_endpoint(
    request: Request,
    chat_request: ChatRequest,
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
    user_timezone = chat_request.effective_timezone  # Use property
    # user_context = chat_request.user_context  # For future use

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

    async def generate_streaming_response() -> AsyncGenerator[str, None]:
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

            # Create a placeholder message for the AI response to get its ID
            placeholder_message = await history_manager.append_message(
                thread_id=int(thread.id),
                user_id="assistant",
                content="",  # Empty content, will be updated later
            )

            # Send initial metadata with the actual message ID
            yield f"event: metadata\ndata: {json.dumps({'thread_id': str(thread.id), 'user_id': user_id, 'message_id': str(placeholder_message.id)})}\n\n"

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

            # After streaming, update the placeholder message with the full response content
            if placeholder_message.id is not None:
                await history_manager.update_message(
                    placeholder_message.id, full_response
                )

            # --- DRAFT PERSISTENCE AND ID HANDLING (MATCH NON-STREAMING ENDPOINT) ---
            # Extract structured draft data
            draft_data = await agent.get_draft_data()
            from services.chat.models import (
                DraftCalendarChange,
                DraftCalendarEvent,
                DraftEmail,
            )

            structured_drafts = []
            for draft in draft_data:
                draft_type = draft.get("type", "")
                # Determine the content field based on draft type
                if draft_type == "email":
                    content = draft.get("body", "")
                elif draft_type == "calendar_event":
                    content = draft.get("description", "")
                elif draft_type == "calendar_change":
                    content = draft.get("new_description", "")
                else:
                    content = draft.get("content", "")

                # Convert metadata to JSON string
                metadata_json = json.dumps(draft.get("metadata", {}))

                # Persist the draft as a UserDraft (match non-streaming endpoint)
                user_draft = await history_manager.create_user_draft(
                    user_id=user_id,
                    draft_type=draft_type,
                    content=content,
                    metadata=metadata_json,
                    thread_id=int(thread.id),
                )
                draft_id = (
                    str(user_draft.id)
                    if user_draft and user_draft.id is not None
                    else None
                )
                draft_with_id = dict(draft)
                draft_with_id["id"] = draft_id

                if draft_type == "email":
                    structured_drafts.append(DraftEmail(**draft_with_id))
                elif draft_type == "calendar_event":
                    structured_drafts.append(DraftCalendarEvent(**draft_with_id))  # type: ignore[arg-type]
                elif draft_type == "calendar_change":
                    structured_drafts.append(DraftCalendarChange(**draft_with_id))  # type: ignore[arg-type]

            # Send completion event (now with drafts)
            completion_data = {
                "thread_id": str(thread.id),
                "full_response": full_response,
                "status": "completed",
                "drafts": (
                    [d.model_dump() for d in structured_drafts]
                    if structured_drafts
                    else None
                ),
            }
            yield f"event: completed\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            # On error, update the placeholder message with error or delete it if possible
            if (
                "placeholder_message" in locals()
                and getattr(placeholder_message, "id", None) is not None
            ):
                try:
                    # mypy fix: ensure id is int, not Optional[int]
                    message_id = placeholder_message.id
                    if message_id is not None:
                        await history_manager.update_message(
                            message_id, f"[ERROR] {str(e)}"
                        )
                except Exception:
                    pass  # Ignore errors during cleanup
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


@router.get("/threads")
async def list_threads(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """
    List threads for a given user using history_manager.

    CONVERSION PATTERN EXAMPLE: Thread (database) -> ThreadResponse (API)
    This function demonstrates the standard pattern for converting database
    models to API response models.
    """
    from services.chat import history_manager

    user_id = await get_user_id_from_gateway(request)

    # Get database models (Thread objects with int IDs, datetime objects, relationships)
    threads = await history_manager.list_threads(
        user_id, limit=limit + 1, offset=offset
    )
    # Optionally, count total threads for pagination (optional for perf)
    # total_count = await history_manager.count_threads(user_id)
    has_more = len(threads) > limit
    if has_more:
        threads = threads[:-1]

    # CONVERSION: Database Thread models -> API ThreadResponse models
    thread_responses = [
        ThreadResponse(
            thread_id=str(t.id),
            user_id=t.user_id,
            title=t.title,
            created_at=str(t.created_at),
            updated_at=str(t.updated_at),
        )
        for t in threads
    ]
    return JSONResponse(
        {
            "threads": [tr.dict() for tr in thread_responses],
            "has_more": has_more,
            "offset": offset,
            "limit": limit,
            # "total_count": total_count,  # Uncomment if you add counting
        }
    )


@router.get("/threads/{thread_id}/history", response_model=ChatResponse)
async def thread_history(
    thread_id: str,
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
async def feedback_endpoint(
    request: Request,
    feedback_request: FeedbackRequest,
) -> FeedbackResponse:
    """
    Receive user feedback for a message.
    """
    user_id = await get_user_id_from_gateway(request)

    # Create feedback request with user_id from gateway header
    feedback_data = Feedback(
        user_id=user_id,
        thread_id=feedback_request.thread_id,
        message_id=feedback_request.message_id,
        feedback=feedback_request.feedback,
    )

    FEEDBACKS.append(feedback_data)
    return FeedbackResponse(status="success", detail="Feedback recorded")


# User Draft Endpoints
@router.post("/drafts", response_model=UserDraftResponse)
async def create_user_draft_endpoint(
    request: Request,
    draft_request: UserDraftRequest,
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


@router.get("/drafts", response_model=UserDraftListResponse)
async def list_user_drafts_endpoint(
    request: Request,
    draft_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
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


@router.get("/drafts/{draft_id}", response_model=UserDraftResponse)
async def get_user_draft_endpoint(
    request: Request,
    draft_id: str,
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


@router.put("/drafts/{draft_id}", response_model=UserDraftResponse)
async def update_user_draft_endpoint(
    request: Request,
    draft_id: str,
    draft_request: UserDraftRequest,
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


class DeleteUserDraftResponse(BaseModel):
    status: str
    message: str


@router.delete("/drafts/{draft_id}", response_model=DeleteUserDraftResponse)
async def delete_user_draft_endpoint(
    request: Request,
    draft_id: str,
) -> DeleteUserDraftResponse:
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

    return DeleteUserDraftResponse(
        status="success", message="Draft deleted successfully"
    )
