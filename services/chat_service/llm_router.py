"""
LLM router using LiteLLM and LangChain memory for chat service.
Stores per user, per-thread conversation history using ConversationTokenBufferMemory.
Provides generate_response to handle ChatRequest and produce ChatResponse.
"""

import uuid
from datetime import datetime
from typing import Dict

import logging
import tiktoken
from langchain.memory import ConversationTokenBufferMemory
from langchain.schema import AIMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from litellm import LiteLLM

from .models import ChatRequest, ChatResponse, Message

# Initialize LiteLLM client (using openai by default)
_litellm = LiteLLM()
# Memory and metadata stores per conversation
_memory_store: Dict[str, ConversationTokenBufferMemory] = {}
_thread_metadata: Dict[str, Dict[str, str]] = {}

# Set up logging
logger = logging.getLogger("chat_service.llm_router")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


def _tiktoken_length_function(text: str, model_name: str = "gpt-4.1-nano") -> int:
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except Exception:
        print(f"Warning: Model {model_name} not found in tiktoken. "
              "Using cl100k_base encoding.")
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class LiteLLMLangChainWrapper(BaseChatModel):
    def __init__(self, litellm_client, model="gpt-4.1-nano", **kwargs):
        super().__init__(**kwargs)
        self._litellm_client = litellm_client
        self._model = model

    @property
    def _llm_type(self):
        return "litellm"

    def _generate(self, messages, stop=None, **kwargs):
        litellm_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                litellm_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                litellm_messages.append({"role": "assistant", "content": msg.content})
        # Log input messages to LLM, one per line
        input_log = "\n".join([f"{m['role']}: {m['content']}" for m in litellm_messages])
        logger.info(f"LLM input messages:\n{input_log}")
        # Log input token count
        input_text = "\n".join([m["content"] for m in litellm_messages])
        input_tokens = len(self.get_token_ids(input_text))
        resp = self._litellm_client.chat.completions.create(
            messages=litellm_messages, model=self._model, stream=False
        )
        content = None
        if hasattr(resp, "choices"):
            choice = resp.choices[0]
            content = getattr(choice.message, "content", None)
        if content is None and hasattr(resp, "text"):
            content = resp.text
        if content is None:
            content = str(resp)
        # Log output token count
        output_tokens = len(self.get_token_ids(content or ""))
        # Log input and output token counts in one line
        logger.info(f"LLM call tokens: input={input_tokens}, output={output_tokens}")
        return AIMessage(content=content)

    def get_token_ids(self, text: str) -> list[int]:
        try:
            enc = tiktoken.encoding_for_model(self._model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return enc.encode(text)


_litellm_wrapper = LiteLLMLangChainWrapper(_litellm, model="gpt-4.1-nano")


class LoggingConversationTokenBufferMemory(ConversationTokenBufferMemory):
    def _summarize(self, *args, **kwargs):
        logger.info("ConversationTokenBufferMemory: Summarizing history due to token limit.")
        return super()._summarize(*args, **kwargs)


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
        _memory_store[key] = LoggingConversationTokenBufferMemory(
            llm=_litellm_wrapper,  # Use wrapper for summarization
            memory_key="history",
            human_prefix="Human",
            ai_prefix="AI",
            max_token_limit=256, #2048,  # or your preferred limit
            token_counter=lambda text: _tiktoken_length_function(
                text, model_name="gpt-4.1-nano"
            ),
            return_messages=True,  # Optional: return message objects
        )
        now_ts = datetime.now().isoformat()
        _thread_metadata[key] = {"created_at": now_ts, "updated_at": now_ts}
    memory = _memory_store[key]
    memory.chat_memory.add_user_message(request.message)
    # Use the wrapper to generate the response and log token counts, respecting max_token_limit
    history = memory.load_memory_variables({})["history"]
    ai_message = _litellm_wrapper._generate(history)
    content = ai_message.content
    if not content or not content.strip():
        logger.warning(f"LLM returned empty content for user {user_id} in thread {thread_id}. Full AIMessage: {ai_message}")
        content = "Sorry, I couldn't generate a response."
    # Save AI response to memory as a reply to the last user message
    memory.chat_memory.add_ai_message(content)
    # Update metadata for updated_at
    _thread_metadata[key]["updated_at"] = datetime.now().isoformat()
    # Build Message list
    messages = [
        Message(
            message_id="1",
            thread_id=thread_id,
            user_id=user_id,
            llm_generated=True,
            content=content,
            created_at=datetime.now().isoformat(),
        )
    ]
    chat_response = ChatResponse(thread_id=thread_id, messages=messages, draft=None)
    try:
        logger.debug(f"Serialized ChatResponse length: {len(chat_response.json())}")
    except Exception as e:
        logger.warning(f"Could not serialize ChatResponse: {e}")
    return chat_response


def _get_memory_store() -> Dict[str, ConversationTokenBufferMemory]:  # pragma: no cover
    """Internal: expose memory store for thread history."""
    return _memory_store


def _get_thread_metadata() -> Dict[str, Dict[str, str]]:  # pragma: no cover
    """Internal: expose thread metadata."""
    return _thread_metadata
