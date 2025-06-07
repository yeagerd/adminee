from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from .models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    Message,
    Thread,
)

router = APIRouter()

# In-memory storage for demonstration (replace with DB integration)
THREADS: Dict[str, Thread] = {}
MESSAGES: Dict[str, List[Message]] = {}
FEEDBACKS: List[FeedbackRequest] = []


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    # Dummy logic: create thread if not exists, append message
    thread_id = request.thread_id or f"thread_{len(THREADS)+1}"
    if thread_id not in THREADS:
        THREADS[thread_id] = Thread(
            thread_id=thread_id,
            user_id=request.user_id,
            created_at="2025-06-05T00:00:00Z",
            updated_at="2025-06-05T00:00:00Z",
        )
        MESSAGES[thread_id] = []
    msg = Message(
        message_id=f"msg_{len(MESSAGES[thread_id])+1}",
        thread_id=thread_id,
        user_id=request.user_id,
        llm_generated=False,
        content=request.message,
        created_at="2025-06-05T00:00:00Z",
    )
    MESSAGES[thread_id].append(msg)

    # Placeholder LLM response
    response_messages = [
        Message(
            message_id=f"llm_msg_{len(MESSAGES[thread_id]) + 1}",
            thread_id=thread_id,
            user_id=request.user_id,
            llm_generated=True,
            content="This is a dummy response from the LLM.",
            created_at=datetime.now().isoformat(),
        )
    ]
    for response_msg in response_messages:
        MESSAGES[thread_id].append(response_msg)

    # Dummy response
    return ChatResponse(
        thread_id=thread_id,
        messages=response_messages,  # Now returns List[Message]
        draft=None,
    )


@router.get("/threads", response_model=List[Thread])
def list_threads(user_id: str):
    return [t for t in THREADS.values() if t.user_id == user_id]


@router.get("/threads/{thread_id}/history", response_model=ChatResponse)
def thread_history(thread_id: str):
    if thread_id not in MESSAGES:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Dummy response
    return ChatResponse(
        thread_id=thread_id,
        messages=MESSAGES[thread_id],
        draft=None,
    )


@router.post("/feedback", response_model=FeedbackResponse)
def feedback_endpoint(request: FeedbackRequest):
    FEEDBACKS.append(request)
    return FeedbackResponse(status="success")
