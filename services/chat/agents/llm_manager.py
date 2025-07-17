"""
LLM management module for chat_service.
Handles LiteLLM initialization and provides model management.
"""

import logging
import os
from typing import Any, AsyncGenerator, Dict, Generator, Sequence, Union

# noqa: F401 - get_llm_provider is present at runtime, linter is wrong
from litellm.utils import get_llm_provider  # type: ignore
from llama_index.core.base.llms.types import ChatResponse, CompletionResponse, ChatResponseAsyncGen
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.tools import BaseTool
from llama_index.llms.litellm import LiteLLM as LlamaLiteLLM

# Configure logging
logger = logging.getLogger(__name__)


class LoggingLiteLLM(LlamaLiteLLM):
    """A wrapper around LlamaLiteLLM that logs all prompts and responses."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._prompt_logger = logging.getLogger(f"{__name__}.prompts")

    def _log_messages(self, messages: Any, method_name: str) -> None:
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

    def _log_response(self, response: Any, method_name: str) -> None:
        """Log the response from the LLM."""
        self._prompt_logger.info(f"=== {method_name.upper()} LLM RESPONSE ===")
        if hasattr(response, "content"):
            self._prompt_logger.info(f"Response content: {response.content}")
        elif hasattr(response, "response"):
            self._prompt_logger.info(f"Response: {response.response}")
        else:
            self._prompt_logger.info(f"Raw response: {response}")
        self._prompt_logger.info("=== END LLM RESPONSE ===")

    def chat(self, messages: Any, **kwargs: Any) -> Any:
        """Override chat to add logging."""
        self._log_messages(messages, "chat")
        response = super().chat(messages, **kwargs)
        self._log_response(response, "chat")
        return response

    async def achat(self, messages: Any, **kwargs: Any) -> Any:
        """Override async chat to add logging."""
        self._log_messages(messages, "achat")
        response = await super().achat(messages, **kwargs)
        self._log_response(response, "achat")
        return response

    def complete(self, prompt: Any, **kwargs: Any) -> Any:
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

    async def acomplete(self, prompt: Any, **kwargs: Any) -> Any:
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


class LoggingFunctionCallingLLM(FunctionCallingLLM):
    """A FunctionCallingLLM with prompt/response logging."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Create the underlying LLM instance
        self._llm = LlamaLiteLLM(*args, **kwargs)
        self._prompt_logger = logging.getLogger(f"{__name__}.prompts")

    def chat(self, messages: Any, **kwargs: Any) -> Any:
        self._prompt_logger.info(f"=== CHAT LLM CALL ===\nMessages: {messages}")
        response = self._llm.chat(messages, **kwargs)
        self._prompt_logger.info(f"=== CHAT LLM RESPONSE ===\nResponse: {response}")
        return response

    async def achat(self, messages: Any, **kwargs: Any) -> Any:
        self._prompt_logger.info(f"=== ACHAT LLM CALL ===\nMessages: {messages}")
        response = await self._llm.achat(messages, **kwargs)
        self._prompt_logger.info(f"=== ACHAT LLM RESPONSE ===\nResponse: {response}")
        return response

    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        self._prompt_logger.info(f"=== COMPLETE LLM CALL ===\nPrompt: {prompt}")
        response = self._llm.complete(prompt, formatted=formatted, **kwargs)
        self._prompt_logger.info(f"=== COMPLETE LLM RESPONSE ===\nResponse: {response}")
        return response

    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        self._prompt_logger.info(f"=== ACOMPLETE LLM CALL ===\nPrompt: {prompt}")
        response = await self._llm.acomplete(prompt, formatted=formatted, **kwargs)
        self._prompt_logger.info(
            f"=== ACOMPLETE LLM RESPONSE ===\nResponse: {response}"
        )
        return response

    # Implement required abstract methods as pass-throughs or raise NotImplementedError
    @property
    def metadata(self) -> Any:
        return self._llm.metadata

    def _prepare_chat_with_tools(self, *args: Any, **kwargs: Any) -> Any:
        return self._llm._prepare_chat_with_tools(*args, **kwargs)

    def stream_chat(self, *args: Any, **kwargs: Any) -> Any:
        return self._llm.stream_chat(*args, **kwargs)

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        result = await self._llm.astream_chat(messages, **kwargs)
        if hasattr(result, "__aiter__"):
            async for event in result:
                yield event
        else:
            # It's a single response
            yield result  # type: ignore[reportReturnType]

    def stream_complete(self, *args: Any, **kwargs: Any) -> Any:
        return self._llm.stream_complete(*args, **kwargs)

    async def astream_complete(self, *args: Any, **kwargs: Any) -> Any:
        return await self._llm.astream_complete(*args, **kwargs)

    def get_tool_calls_from_response(
        self, response: Any, error_on_no_tool_call: bool = True, **kwargs: Any
    ) -> Any:
        """Get tool calls from response."""
        return self._llm.get_tool_calls_from_response(
            response, error_on_no_tool_call, **kwargs
        )


class FakeLLM(FunctionCallingLLM):
    """A fake LLM for testing and offline mode that's compatible with LlamaIndex and supports function calling."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm = LlamaLiteLLM(model="fake-model", **kwargs)
        self._metadata = {
            "model_name": "fake-llm",
            "is_chat_model": True,
            "is_function_calling_model": True,
        }
        logger.warning("Using FakeLLM - no actual LLM calls are being made")

    @property
    def llm(self) -> Any:
        return self._llm

    @property
    def metadata(self) -> Any:
        """Return LLM metadata."""

        # Create a simple object with the required attributes
        class SimpleMetadata:
            def __init__(self) -> None:
                self.model_name = "fake-llm"
                self.is_chat_model = True
                self.is_function_calling_model = True
                self.context_window = 4096  # Default context window for fake LLM
                self.num_output = 512  # Default max output tokens

        return SimpleMetadata()

    def _chat(
        self, messages: Sequence[Union[ChatMessage, Dict[str, Any]]], **kwargs: Any
    ) -> ChatMessage:
        """Fake chat method that just echoes back the last user message."""
        from llama_index.core.llms import ChatMessage, MessageRole

        # Handle case where messages is a list of dicts or ChatMessage objects
        user_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    user_messages.append(msg)
            elif hasattr(msg, "role") and msg.role == "user":
                user_messages.append(msg)  # type: ignore[arg-type]

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

    def _complete(self, prompt: str, **kwargs: Any) -> str:
        """Fake complete method that just echoes back the prompt."""
        return f"[FAKE LLM RESPONSE] You said: {prompt}"

    def _stream_complete(
        self, prompt: str, **kwargs: Any
    ) -> Generator[str, None, None]:
        """Fake stream complete method."""
        yield self._complete(prompt, **kwargs)

    def _prepare_chat_with_tools(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Prepare chat with tools (no-op for fake LLM)."""
        return {}

    def chat_with_tools(self, *args: Any, **kwargs: Any) -> Any:
        """Fake chat with tools method."""
        return self._chat(*args, **kwargs)

    async def achat_with_tools(self, *args: Any, **kwargs: Any) -> Any:
        """Fake async chat with tools method."""
        return self._chat(*args, **kwargs)

    def chat(
        self, messages: Sequence[Union[ChatMessage, Dict[str, Any]]], **kwargs: Any
    ) -> ChatResponse:
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

        response_text = f"[FAKE LLM RESPONSE] You said: {last_user_message}"
        chat_msg = ChatMessage(role=MessageRole.ASSISTANT, content=response_text)
        return ChatResponse(
            message=chat_msg,
            delta=response_text,
            raw={"model": "fake-model", "usage": {"total_tokens": 0}},
            logprobs=None,
        )

    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        """Async fake chat method that just echoes back the last user message."""
        return self.chat(messages, **kwargs)

    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        """Fake complete method that just echoes back the prompt."""
        response_text = f"[FAKE LLM RESPONSE] You said: {prompt}"
        return CompletionResponse(
            text=response_text,
            raw={"model": "fake-model", "usage": {"total_tokens": 0}},
            logprobs=None,
        )

    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        """Async fake complete method that just echoes back the prompt."""
        return self.complete(prompt, formatted=formatted, **kwargs)

    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> Generator[ChatResponse, None, None]:
        """Fake stream chat method."""
        response = self.chat(messages, **kwargs)
        yield response

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> AsyncGenerator[ChatResponse, None]:
        """Async fake stream chat method."""
        response = await self.achat(messages, **kwargs)
        yield response

    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> Generator[CompletionResponse, None, None]:
        """Fake stream complete method."""
        yield self.complete(prompt, formatted=formatted, **kwargs)

    async def astream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> AsyncGenerator[CompletionResponse, None]:
        """Async fake stream complete method."""

        async def gen() -> AsyncGenerator[CompletionResponse, None]:
            yield self.complete(prompt, formatted=formatted, **kwargs)

        return gen()

    async def astream_chat_with_tools(
        self,
        tools: Sequence[BaseTool],
        user_msg: Union[str, ChatMessage, None] = None,
        chat_history: list[ChatMessage] | None = None,
        verbose: bool = False,
        allow_parallel_tool_calls: bool = True,
        tool_required: bool = False,
        **kwargs: Any,
    ) -> AsyncGenerator[ChatResponse, None]:
        async def gen() -> AsyncGenerator[ChatResponse, None]:
            messages = chat_history or []
            response = self.chat(messages, **kwargs)
            yield response

        return gen()


class _LLMManager:
    """
    Manages LLM instances with LiteLLM, providing a unified interface for different models.
    """

    _instance = None

    def __new__(cls) -> "_LLMManager":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def get_llm(self, model: str, provider: str, **kwargs: Any) -> Any:
        """
        Get an LLM instance with the specified model and provider.
        Returns a LiteLLM instance or FakeLLM if no API key is found.

        Args:
            model: The model name (e.g., 'gpt-4.1-nano')
            provider: The provider name (e.g., 'openai', 'anthropic')
            **kwargs: Additional arguments to pass to the LLM

        Returns:
            A LiteLLM instance, or FakeLLM if no API key is found
        """
        if provider == "fake":
            return FakeLLM()

        # Check if we have the required API key
        api_key_env = f"{provider.upper()}_API_KEY"
        if not os.getenv(
            api_key_env
        ):  # No need to check provider != "fake" here due to the above
            logger.warning(
                f"No {api_key_env} environment variable found. "
                "Falling back to FakeLLM. Set the appropriate API key to use a real LLM."
            )
            return FakeLLM()

        # Create a LiteLLM compatible model string
        # Provider will not be "fake" here, so this logic is fine.
        if "/" not in model and provider:
            model = f"{provider}/{model}"

        # Some models support language parameters
        llm_kwargs = kwargs.copy()
        if "language" not in llm_kwargs:
            llm_kwargs["language"] = "en"

        # Always use FunctionCallingLLM for real LLMs
        return LoggingFunctionCallingLLM(model=model, **llm_kwargs)

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: The model name

        Returns:
            Dictionary containing model information
        """
        try:
            model_name, provider, *_ = get_llm_provider(model)
            return {
                "model": model,
                "provider": provider,
                "default": False,
            }
        except Exception as e:
            return {
                "model": model,
                "error": str(e),
                "default": False,
            }


def get_llm_manager() -> _LLMManager:
    """
    Returns a singleton instance of the _LLMManager.
    Initializes the instance upon first call.
    """
    return _LLMManager()
