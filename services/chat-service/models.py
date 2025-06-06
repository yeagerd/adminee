from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    user_id: str
    thread_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    thread_id: str
    messages: List[dict]  # Should be refined to a Message model
    draft: Optional[dict] = None  # Placeholder for draft email/calendar event

class Thread(BaseModel):
    thread_id: str
    user_id: str
    created_at: str
    updated_at: str

class Message(BaseModel):
    message_id: str
    thread_id: str
    user_id: str
    content: str
    created_at: str

class FeedbackRequest(BaseModel):
    user_id: str
    thread_id: str
    message_id: str
    feedback: str  # 'up' or 'down'

class FeedbackResponse(BaseModel):
    status: str
    detail: Optional[str] = None
