"""
LLM management module for common service.

Handles LiteLLM initialization and provides model management for services
that need LLM capabilities.
"""

import logging
import os
from typing import Any

from litellm import completion

from services.common.logging_config import get_logger

logger = get_logger(__name__)


class LLMManager:
    """
    Manages LLM instances with LiteLLM, providing a unified interface for different models.
    """

    _instance = None

    def __new__(cls) -> "LLMManager":
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
        if not os.getenv(api_key_env):
            logger.warning(
                f"No {api_key_env} environment variable found. "
                "Falling back to FakeLLM. Set the appropriate API key to use a real LLM."
            )
            return FakeLLM()

        # Create a LiteLLM compatible model string
        if "/" not in model and provider:
            model = f"{provider}/{model}"

        # Some models support language parameters, but not all
        llm_kwargs = kwargs.copy()
        # Remove language parameter as it's not supported by all models
        llm_kwargs.pop("language", None)

        return RealLLM(model=model, **llm_kwargs)


class FakeLLM:
    """Fake LLM for testing and when no API key is available."""

    def __init__(self, **kwargs: Any) -> None:
        self.model = kwargs.get("model", "fake-model")
        self._prompt_logger = logging.getLogger(f"{__name__}.prompts")

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Fake complete method that just echoes back the prompt."""
        self._prompt_logger.info(f"=== FAKE LLM CALL ===\nPrompt: {prompt}")
        response = f"[FAKE LLM RESPONSE] You said: {prompt}"
        self._prompt_logger.info(f"=== FAKE LLM RESPONSE ===\nResponse: {response}")
        return response

    async def acomplete(self, prompt: str, **kwargs: Any) -> str:
        """Async fake complete method."""
        return self.complete(prompt, **kwargs)


class RealLLM:
    """Real LLM using LiteLLM for actual API calls."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.kwargs = kwargs
        self._prompt_logger = logging.getLogger(f"{__name__}.prompts")

        # Try to import cache (may not be available in common service)
        try:
            from services.shipments.llm_cache import get_llm_cache

            self.cache = get_llm_cache()
        except ImportError:
            self.cache = None

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Complete a prompt using LiteLLM with caching."""
        # Merge kwargs
        call_kwargs = {**self.kwargs, **kwargs}

        # Check cache first
        if self.cache:
            cached_response = self.cache.get(
                model=self.model, prompt=prompt, **call_kwargs
            )
            if cached_response:
                logger.debug(f"Using cached response for {self.model}")
                return cached_response["response"]

        self._prompt_logger.info(
            f"=== REAL LLM CALL ===\nModel: {self.model}\nPrompt: {prompt}"
        )

        try:
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **call_kwargs,
            )

            # Extract content from response
            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content
                if content is None:
                    content = str(response)
            else:
                content = str(response)

            self._prompt_logger.info(f"=== REAL LLM RESPONSE ===\nResponse: {content}")

            # Cache the response
            if self.cache:
                self.cache.set(
                    model=self.model, response=content, prompt=prompt, **call_kwargs
                )

            return content

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"[LLM ERROR] {str(e)}"

    async def acomplete(self, prompt: str, **kwargs: Any) -> str:
        """Async complete method (synchronous for now)."""
        return self.complete(prompt, **kwargs)


def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    return LLMManager()
