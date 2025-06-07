from typing import List

from fastapi import APIRouter, HTTPException
from langchain.schema import AIMessage

from .langchain_router import _get_memory_store, _get_thread_metadata, generate_response
from .models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    Message,
    Thread,
)

router = APIRouter()

# In-memory feedback storage
FEEDBACKS: List[FeedbackRequest] = []


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint using LLM router with memory.
    """
    return generate_response(request)


@router.get("/threads", response_model=List[Thread])
def list_threads(user_id: str) -> List[Thread]:
    """
    List threads for a given user using metadata store.
    """
    threads: List[Thread] = []
    metadata = _get_thread_metadata()
    for key, meta in metadata.items():
        uid, tid = key.split(":", 1)
        if uid == user_id:
            threads.append(
                Thread(
                    thread_id=tid,
                    user_id=uid,
                    created_at=meta["created_at"],
                    updated_at=meta["updated_at"],
                )
            )
    return threads


@router.get("/threads/{thread_id}/history", response_model=ChatResponse)
def thread_history(thread_id: str) -> ChatResponse:
    """
    Get chat history for a given thread using memory store.
    """
    metadata = _get_thread_metadata()
    store = _get_memory_store()
    key = next((k for k in store.keys() if k.endswith(f":{thread_id}")), None)
    if not key:
        raise HTTPException(status_code=404, detail="Thread not found")
    user_id = key.split(":", 1)[0]
    memory = store[key]
    messages: List[Message] = []
    for idx, msg in enumerate(memory.chat_memory.messages):
        llm_generated = isinstance(msg, AIMessage)
        messages.append(
            Message(
                message_id=str(idx + 1),
                thread_id=thread_id,
                user_id=user_id,
                llm_generated=llm_generated,
                content=msg.content,
                created_at=metadata[key]["updated_at"],
            )
        )
    return ChatResponse(thread_id=thread_id, messages=messages, draft=None)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback_endpoint(request: FeedbackRequest) -> FeedbackResponse:
    """
    Receive user feedback for a message.
    """
    FEEDBACKS.append(request)
    return FeedbackResponse(status="success")
