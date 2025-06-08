import asyncio
from typing import List

from fastapi import APIRouter

from services.chat_service.llama_manager import ChatAgentManager

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
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint using llama_manager ChatAgentManager.
    """
    # NOTE: FastAPI sync endpoint, so run async agent in event loop
    thread_id = int(request.thread_id) if request.thread_id else 1  # fallback for demo
    user_id = request.user_id
    user_input = request.message
    # TODO: Replace with real LiteLLM instance
    llm = None
    agent = ChatAgentManager(
        llm=llm,
        thread_id=thread_id,
        user_id=user_id,
        tools=[],
        subagents=[],
    )
    # reply = asyncio.get_event_loop().run_until_complete(agent.chat(user_input))
    # Fetch updated history for response
    messages = asyncio.get_event_loop().run_until_complete(agent.get_memory(user_input))
    return ChatResponse(messages=messages)


@router.get("/threads", response_model=List[Thread])
def list_threads(user_id: str) -> List[Thread]:
    """
    List threads for a given user using history_manager.
    """
    import asyncio

    from services.chat_service import history_manager

    threads = asyncio.get_event_loop().run_until_complete(
        history_manager.list_threads(user_id)
    )
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
def thread_history(thread_id: str) -> ChatResponse:
    """
    Get chat history for a given thread using history_manager.
    """
    import asyncio

    from services.chat_service import history_manager
    from services.chat_service.models import Message

    messages = asyncio.get_event_loop().run_until_complete(
        history_manager.get_thread_history(int(thread_id), limit=100)
    )
    chat_messages = [
        Message(
            message_id=str(i + 1),
            thread_id=str(thread_id),
            user_id=m.user_id,
            llm_generated=(m.user_id != messages[0].user_id if messages else False),
            content=m.content,
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
