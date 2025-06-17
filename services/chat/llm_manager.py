"""
LLM management module for chat_service.
Handles LiteLLM initialization and provides model management.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

from litellm.utils import get_llm_provider
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.llms.litellm import LiteLLM as LlamaLiteLLM

# Configure logging
logger = logging.getLogger(__name__)


class LoggingLiteLLM(LlamaLiteLLM):
    """A wrapper around LlamaLiteLLM that logs all prompts and responses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prompt_logger = logging.getLogger(f"{__name__}.prompts")

    def _log_messages(self, messages, method_name: str):
        """Log the messages being sent to the LLM."""
        self._prompt_logger.info(f"=== {method_name.upper()} LLM CALL ===")
        self._prompt_logger.info(f"Model: {getattr(self, 'model', 'unknown')}")
        self._prompt_logger.info(
            f"Number of messages: {len(messages) if messages else 0}"
        )

        if messages:
            for i, msg in enumerate(messages):
                if hasattr(msg, "role") and hasattr(msg, "content"):
                    # ChatMessage object
                    role = (
                        str(msg.role).upper()
                        if hasattr(msg.role, "__str__")
                        else str(msg.role)
                    )
                    content = msg.content
                elif isinstance(msg, dict):
                    # Dictionary format
                    role = msg.get("role", "unknown").upper()
                    content = msg.get("content", "")
                else:
                    # String or other format
                    role = "UNKNOWN"
                    content = str(msg)

                self._prompt_logger.info(f"Message {i+1} [{role}]: {content}")

        self._prompt_logger.info("=== END LLM CALL ===")

    def _log_response(self, response, method_name: str):
        """Log the response from the LLM."""
        self._prompt_logger.info(f"=== {method_name.upper()} LLM RESPONSE ===")
        if hasattr(response, "content"):
            self._prompt_logger.info(f"Response content: {response.content}")
        elif hasattr(response, "response"):
            self._prompt_logger.info(f"Response: {response.response}")
        else:
            self._prompt_logger.info(f"Raw response: {response}")
        self._prompt_logger.info("=== END LLM RESPONSE ===")

    def chat(self, messages, **kwargs):
        """Override chat to add logging."""
        self._log_messages(messages, "chat")
        response = super().chat(messages, **kwargs)
        self._log_response(response, "chat")
        return response

    async def achat(self, messages, **kwargs):
        """Override async chat to add logging."""
        self._log_messages(messages, "achat")
        response = await super().achat(messages, **kwargs)
        self._log_response(response, "achat")
        return response

    def complete(self, prompt, **kwargs):
        """Override complete to add logging."""
        self._prompt_logger.info("=== COMPLETE LLM CALL ===")
        self._prompt_logger.info(f"Model: {getattr(self, 'model', 'unknown')}")
        self._prompt_logger.info(f"Prompt: {prompt}")
        self._prompt_logger.info("=== END LLM CALL ===")

        response = super().complete(prompt, **kwargs)

        self._prompt_logger.info("=== COMPLETE LLM RESPONSE ===")
        self._prompt_logger.info(f"Response: {response}")
        self._prompt_logger.info("=== END LLM RESPONSE ===")

        return response

    async def acomplete(self, prompt, **kwargs):
        """Override async complete to add logging."""
        self._prompt_logger.info("=== ACOMPLETE LLM CALL ===")
        self._prompt_logger.info(f"Model: {getattr(self, 'model', 'unknown')}")
        self._prompt_logger.info(f"Prompt: {prompt}")
        self._prompt_logger.info("=== END LLM CALL ===")

        response = await super().acomplete(prompt, **kwargs)

        self._prompt_logger.info("=== ACOMPLETE LLM RESPONSE ===")
        self._prompt_logger.info(f"Response: {response}")
        self._prompt_logger.info("=== END LLM RESPONSE ===")

        return response


class FakeLLM(FunctionCallingLLM):
    """A fake LLM for testing and offline mode that's compatible with LlamaIndex and supports function calling."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._llm = LlamaLiteLLM(model="fake-model", **kwargs)
        self._metadata = {
            "model_name": "fake-llm",
            "is_chat_model": True,
            "is_function_calling_model": True,
        }
        logger.warning("Using FakeLLM - no actual LLM calls are being made")

    @property
    def llm(self):
        return self._llm

    @property
    def metadata(self):
        """Return LLM metadata."""

        # Create a simple object with the required attributes
        class SimpleMetadata:
            def __init__(self):
                self.model_name = "fake-llm"
                self.is_chat_model = True
                self.is_function_calling_model = True
                self.context_window = 4096  # Default context window for fake LLM
                self.num_output = 512  # Default max output tokens

        return SimpleMetadata()

    def _chat(self, messages, **kwargs):
        """Fake chat method that just echoes back the last user message."""
        from llama_index.core.llms import ChatMessage, MessageRole

        # Handle case where messages is a list of dicts or ChatMessage objects
        user_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    user_messages.append(msg)
            elif hasattr(msg, "role") and msg.role == "user":
                user_messages.append(msg)

        last_user_message = ""
        if user_messages:
            last_msg = user_messages[-1]
            last_user_message = (
                last_msg.get("content", "")
                if isinstance(last_msg, dict)
                else last_msg.content
            )

        response_text = f"[FAKE LLM RESPONSE] You said: {last_user_message}"
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response_text,
        )

    def _complete(self, prompt, **kwargs):
        """Fake complete method that just echoes back the prompt."""
        return f"[FAKE LLM RESPONSE] You said: {prompt}"

    def _stream_chat(self, messages, **kwargs):
        """Fake stream chat method."""
        response = self._chat(messages, **kwargs)
        yield response

    def _stream_complete(self, prompt, **kwargs):
        """Fake stream complete method."""
        yield self._complete(prompt, **kwargs)

    def _prepare_chat_with_tools(self, *args, **kwargs):
        """Prepare chat with tools (no-op for fake LLM)."""
        return {}

    def chat_with_tools(self, *args, **kwargs):
        """Fake chat with tools method."""
        return self._chat(*args, **kwargs)

    async def achat_with_tools(self, *args, **kwargs):
        """Fake async chat with tools method."""
        return await self._chat(*args, **kwargs)

    def chat(self, messages: List[Union[ChatMessage, Dict]], **kwargs) -> ChatMessage:
        """Fake chat method that just echoes back the last user message."""
        # Convert dict messages to ChatMessage if needed
        processed_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                processed_messages.append(
                    ChatMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        **{
                            k: v for k, v in msg.items() if k not in ["role", "content"]
                        },
                    )
                )
            else:
                processed_messages.append(msg)

        user_messages = [
            msg for msg in processed_messages if msg.role == MessageRole.USER
        ]
        last_user_message = (
            user_messages[-1].content if user_messages else "No user message found"
        )

        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=f"[FAKE LLM RESPONSE] You said: {last_user_message}",
        )

    async def achat(self, messages: List[ChatMessage], **kwargs) -> ChatMessage:
        """Async fake chat method that just echoes back the last user message."""
        return self.chat(messages, **kwargs)

    def complete(self, prompt: str, **kwargs) -> str:
        """Fake complete method that just echoes back the prompt."""
        return f"[FAKE LLM RESPONSE] You said: {prompt}"

    async def acomplete(self, prompt: str, **kwargs) -> str:
        """Async fake complete method that just echoes back the prompt."""
        return self.complete(prompt, **kwargs)

    def stream_chat(self, messages: List[ChatMessage], **kwargs):
        """Fake stream chat method."""
        response = self.chat(messages, **kwargs)
        yield response

    async def astream_chat(self, messages: List[ChatMessage], **kwargs):
        """Async fake stream chat method."""
        response = await self.achat(messages, **kwargs)
        yield response

    def stream_complete(self, prompt: str, **kwargs):
        """Fake stream complete method."""
        yield self.complete(prompt, **kwargs)

    async def astream_complete(self, prompt: str, **kwargs):
        """Async fake stream complete method."""
        yield await self.acomplete(prompt, **kwargs)


class _LLMManager:
    """
    Manages LLM instances with LiteLLM, providing a unified interface for different models.
    """

    _instance = None
    _default_provider: str
    _default_model: str

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(_LLMManager, cls).__new__(cls)
            cls._default_provider = os.getenv("LLM_PROVIDER", "openai")
            cls._default_model = os.getenv("LLM_MODEL", "gpt-4.1-nano")
        return cls._instance

    def get_llm(
        self, model: Optional[str] = None, provider: Optional[str] = None, **kwargs
    ) -> Any:
        """
        Get an LLM instance with the specified model and provider.
        Returns a LiteLLM instance or FakeLLM if no API key is found.

        Args:
            model: The model name (e.g., 'gpt-3.5-turbo')
            provider: The provider name (e.g., 'openai', 'anthropic')
            **kwargs: Additional arguments to pass to the LLM

        Returns:
            A LiteLLM instance, or FakeLLM if no API key is found
        """
        model = model or self._default_model
        provider = provider or self._default_provider

        # Check if we have the required API key
        api_key_env = f"{provider.upper()}_API_KEY"
        if not os.getenv(api_key_env) and provider != "fake":
            logger.warning(
                f"No {api_key_env} environment variable found. "
                "Falling back to FakeLLM. Set the appropriate API key to use a real LLM."
            )
            return FakeLLM()

        # Create a LiteLLM compatible model string
        if "/" not in model and provider:
            model = f"{provider}/{model}"

        # Some models support language parameters
        llm_kwargs = kwargs.copy()
        if "language" not in llm_kwargs:
            llm_kwargs["language"] = "en"

        # Return a LoggingLiteLLM instance with language settings for prompt logging
        return LoggingLiteLLM(model=model, **llm_kwargs)

    def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: The model name (uses default if not specified)

        Returns:
            Dictionary containing model information
        """
        model = model or self._default_model
        try:
            provider, _ = get_llm_provider(model)
            return {
                "model": model,
                "provider": provider,
                "default": model == self._default_model,
            }
        except Exception as e:
            return {
                "model": model,
                "error": str(e),
                "default": model == self._default_model,
            }


# Global instance
_llm_manager_instance: Optional[_LLMManager] = None

def get_llm_manager() -> _LLMManager:
    """
    Returns a singleton instance of the _LLMManager.
    Initializes the instance upon first call.
    """
    global _llm_manager_instance
    if _llm_manager_instance is None:
        _llm_manager_instance = _LLMManager()
    return _llm_manager_instance
