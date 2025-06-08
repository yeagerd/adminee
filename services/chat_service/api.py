import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from services.chat_service.llama_manager import ChatAgentManager
from services.chat_service.models import Message as PydanticMessage

from .models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    Thread,
)

router = APIRouter()

# In-memory feedback storage
FEEDBACKS: List[FeedbackRequest] = []


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint using llama_manager ChatAgentManager.
    """
    from typing import cast

    from services.chat_service import history_manager

    user_id = request.user_id
    thread_id = request.thread_id
    user_input = request.message

    # Create or get thread
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

    # Initialize the agent with LLM from LLMManager
    agent = ChatAgentManager(
        thread_id=thread.id,
        user_id=user_id,
        tools=[],
        subagents=[],
        # These will use environment variables if not specified
        llm_model=os.getenv("LLM_MODEL"),
        llm_provider=os.getenv("LLM_PROVIDER"),
    )
    # Actually run the chat to append messages
    await agent.chat(user_input)
    # Fetch messages as ORM objects
    orm_messages = await agent.get_memory(user_input)
    # Convert to Pydantic Message models
    pydantic_messages = []
    for m in orm_messages:
        # If already a dict, convert fields
        if isinstance(m, dict):
            pydantic_messages.append(
                PydanticMessage(
                    message_id=str(m.get("id") or m.get("message_id")),
                    thread_id=str(
                        m.get("thread_id")
                        or m.get("thread", {}).get("id")
                        or request.thread_id
                        or 1
                    ),
                    user_id=(
                        str(m.get("user_id")) if m.get("user_id") is not None else ""
                    ),
                    llm_generated=(m.get("user_id") != request.user_id),
                    content=(
                        str(m.get("content")) if m.get("content") is not None else ""
                    ),
                    created_at=str(m.get("created_at")),
                )
            )
        else:
            # fallback: assume already a Pydantic Message
            pydantic_messages.append(m)
    return ChatResponse(
        thread_id=str(agent.thread_id), messages=pydantic_messages, draft=None
    )


@router.get("/threads", response_model=List[Thread])
async def list_threads(user_id: str) -> List[Thread]:
    """
    List threads for a given user using history_manager.
    """
    from services.chat_service import history_manager

    threads = await history_manager.list_threads(user_id)
    return [
        Thread(
            thread_id=str(t.id),
            user_id=t.user_id,
            created_at=str(t.created_at),
            updated_at=str(t.updated_at),
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}/history", response_model=ChatResponse)
async def thread_history(thread_id: str) -> ChatResponse:
    """
    Get chat history for a given thread using history_manager.
    """
    from services.chat_service import history_manager
    from services.chat_service.models import Message

    messages = await history_manager.get_thread_history(int(thread_id), limit=100)
    chat_messages = [
        Message(
            message_id=str(i + 1),
            thread_id=str(thread_id),
            user_id=str(m.user_id) if m.user_id is not None else "",
            llm_generated=(m.user_id != messages[0].user_id if messages else False),
            content=str(m.content) if m.content is not None else "",
            created_at=str(m.created_at),
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
