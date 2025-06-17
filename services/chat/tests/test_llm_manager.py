import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure get_llm_manager is imported correctly
from services.chat.agents.llm_manager import (
    FakeLLM,
    _LLMManager,
    get_llm_manager,
)


# Reset the singleton instance before each test to ensure isolation
@pytest.fixture(autouse=True)
def reset_llm_manager_singleton():
    _LLMManager._instance = None
    yield
    _LLMManager._instance = None


@pytest.fixture
def llm_manager():
    return get_llm_manager()


def test_get_llm_success_fake_provider(llm_manager):
    """Test get_llm returns FakeLLM for 'fake' provider."""
    llm = llm_manager.get_llm(model="fake-model", provider="fake")
    assert isinstance(llm, FakeLLM)


@patch.dict(os.environ, {}, clear=True)  # Ensure no API keys are present
def test_get_llm_fallback_to_fake_llm_if_api_key_missing(llm_manager):
    """Test get_llm falls back to FakeLLM if API key is missing for a real provider."""
    llm = llm_manager.get_llm(model="gpt-3.5-turbo", provider="openai")
    assert isinstance(llm, FakeLLM)


@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}, clear=True)
def test_get_llm_success_real_provider_with_api_key(llm_manager):
    """Test get_llm returns LoggingLiteLLM for a real provider if API key is present."""
    # We expect this to try to create a LoggingLiteLLM instance.
    # Since LiteLLM might try to make network calls or validate the key,
    # we'll patch LoggingLiteLLM to prevent actual instantiation issues in this unit test.
    with patch("services.chat.agents.llm_manager.LoggingLiteLLM") as mock_logging_llm:
        mock_logging_llm_instance = MagicMock()
        mock_logging_llm.return_value = mock_logging_llm_instance

        llm = llm_manager.get_llm(model="gpt-3.5-turbo", provider="openai")
        mock_logging_llm.assert_called_once_with(
            model="openai/gpt-3.5-turbo", language="en"
        )
        assert llm is mock_logging_llm_instance


def test_get_llm_missing_model_arg(llm_manager):
    """Test get_llm raises TypeError if model argument is missing."""
    with pytest.raises(
        TypeError, match=r".*missing 1 required positional argument: 'model'.*"
    ):
        llm_manager.get_llm(provider="fake")


def test_get_llm_missing_provider_arg(llm_manager):
    """Test get_llm raises TypeError if provider argument is missing."""
    with pytest.raises(
        TypeError, match=r".*missing 1 required positional argument: 'provider'.*"
    ):
        llm_manager.get_llm(model="fake-model")


def test_get_model_info_success(llm_manager):
    """Test get_model_info returns correct information."""
    # Mock get_llm_provider from litellm.utils to avoid external calls
    with patch(
        "services.chat.agents.llm_manager.get_llm_provider"
    ) as mock_get_provider:
        mock_get_provider.return_value = (
            "openai",
            "gpt-3.5-turbo",
        )  # provider, model_name
        info = llm_manager.get_model_info(model="openai/gpt-3.5-turbo")

    assert info["model"] == "openai/gpt-3.5-turbo"
    assert info["provider"] == "openai"
    assert info["default"] is False  # Default is now always False


def test_get_model_info_missing_model_arg(llm_manager):
    """Test get_model_info raises TypeError if model argument is missing."""
    with pytest.raises(
        TypeError, match=r".*missing 1 required positional argument: 'model'.*"
    ):
        llm_manager.get_model_info()


def test_get_model_info_error_case(llm_manager):
    """Test get_model_info handles errors from get_llm_provider."""
    with patch("litellm.utils.get_llm_provider", side_effect=Exception("Test error")):
        info = llm_manager.get_model_info(model="unknown/model")

    assert info["model"] == "unknown/model"
    assert "error" in info
    assert info["default"] is False


# Test the singleton behavior of get_llm_manager
def test_get_llm_manager_is_singleton():
    manager1 = get_llm_manager()
    manager2 = get_llm_manager()
    assert manager1 is manager2


# Test that the __new__ method is not re-initializing provider/model defaults (already removed)
# This test is more of a conceptual check now, as the attributes are gone.
# We can verify that the instance is created correctly without those attributes.
def test_llm_manager_new_does_not_set_defaults():
    # Reset singleton for this specific test to observe __new__ behavior
    _LLMManager._instance = None
    manager = _LLMManager()  # Directly instantiate
    assert not hasattr(manager, "_default_provider")
    assert not hasattr(manager, "_default_model")
    # Ensure it's the same instance get_llm_manager() would return
    assert manager is get_llm_manager()
