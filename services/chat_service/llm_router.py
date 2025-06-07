"""
LLM router using LiteLLM and LangChain memory for chat service.
Stores per user, per-thread conversation history using ConversationTokenBufferMemory.
Provides generate_response to handle ChatRequest and produce ChatResponse.
"""

import uuid
from datetime import datetime
from typing import Dict

import tiktoken
from langchain.memory import ConversationTokenBufferMemory
from langchain.schema import AIMessage, HumanMessage
from langchain_core.language_models.base import BaseLanguageModel
from litellm import LiteLLM
from pydantic import PrivateAttr

from .models import ChatRequest, ChatResponse, Message

# Initialize LiteLLM client (using openai by default)
_litellm = LiteLLM()
# Memory and metadata stores per conversation
_memory_store: Dict[str, ConversationTokenBufferMemory] = {}
_thread_metadata: Dict[str, Dict[str, str]] = {}


def _tiktoken_length_function(text: str, model_name: str = "gpt-4.1-nano") -> int:
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except Exception:
        print(f"Warning: Model {model_name} not found in tiktoken. "
              "Using cl100k_base encoding.")
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class DummyLLM(BaseLanguageModel):
    @property
    def _llm_type(self):
        return "dummy"

    def _generate(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not generate responses.")

    def predict(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not predict.")

    async def apredict(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not predict asynchronously.")

    def predict_messages(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not predict messages.")

    async def apredict_messages(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not predict messages asynchronously.")

    def generate_prompt(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not generate prompts.")

    async def agenerate_prompt(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not generate prompts asynchronously.")

    def invoke(self, *args, **kwargs):
        raise NotImplementedError("DummyLLM does not invoke.")

    def get_token_ids(self, text: str) -> list[int]:
        # Prevents LangChain from requiring transformers
        return []


_dummy_llm = DummyLLM()


def generate_response(request: ChatRequest) -> ChatResponse:
    """
    Generate a chat response using LiteLLM and LangChain memory.
    """
    user_id = request.user_id
    # Create or reuse thread ID
    thread_id = request.thread_id or f"thread_{uuid.uuid4().hex}"
    key = f"{user_id}:{thread_id}"
    # Initialize memory and metadata if new conversation
    if key not in _memory_store:
        _memory_store[key] = ConversationTokenBufferMemory(
            llm=_dummy_llm,  # Use dummy LLM to satisfy validation
            memory_key="history",
            human_prefix="Human",
            ai_prefix="AI",
            max_token_limit=2048,  # or your preferred limit
            token_counter=lambda text: _tiktoken_length_function(
                text, model_name="gpt-4.1-nano"
            ),
        )
        now_ts = datetime.now().isoformat()
        _thread_metadata[key] = {"created_at": now_ts, "updated_at": now_ts}
    memory = _memory_store[key]
    # Save human message to memory (output must be present, even if empty)
    memory.save_context({"input": request.message}, {"output": ""})
    # Convert history to messages for LiteLLM
    litellm_messages = []
    for msg in memory.chat_memory.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        litellm_messages.append({"role": role, "content": msg.content})
    # Call LiteLLM
    resp = _litellm.chat.completions.create(
        messages=litellm_messages, model="gpt-4.1-nano", stream=False
    )
    # Extract content from response
    content = None
    if hasattr(resp, "choices"):
        choice = resp.choices[0]
        # LiteLLM choices have .message for chat
        content = getattr(choice.message, "content", None)
    if content is None and hasattr(resp, "text"):
        content = resp.text  # type: ignore
    if content is None:
        content = str(resp)
    # Save AI response to memory
    memory.save_context({"input": ""}, {"output": content})
    # Update metadata for updated_at
    _thread_metadata[key]["updated_at"] = datetime.now().isoformat()
    # Build Message list
    messages = []
    for idx, msg in enumerate(memory.chat_memory.messages):
        messages.append(
            Message(
                message_id=str(idx + 1),
                thread_id=thread_id,
                user_id=user_id,
                llm_generated=isinstance(msg, AIMessage),
                content=msg.content,
                created_at=datetime.now().isoformat(),
            )
        )
    return ChatResponse(thread_id=thread_id, messages=messages, draft=None)


def _get_memory_store() -> Dict[str, ConversationTokenBufferMemory]:  # pragma: no cover
    """Internal: expose memory store for thread history."""
    return _memory_store


def _get_thread_metadata() -> Dict[str, Dict[str, str]]:  # pragma: no cover
    """Internal: expose thread metadata."""
    return _thread_metadata
