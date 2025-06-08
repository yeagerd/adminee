from unittest.mock import AsyncMock, patch

import pytest

from services.chat_service import context_module as cm

MESSAGES = [{"content": f"Message {i}"} for i in range(10)]
USER_INPUT = "What is the summary?"


def test_count_tokens():
    tokens = cm.count_tokens("hello world", model="gpt-3.5-turbo")
    assert isinstance(tokens, int)
    assert tokens > 0


def test_select_relevant_messages_fits():
    selected = cm.select_relevant_messages(MESSAGES, USER_INPUT, 1000, "gpt-3.5-turbo")
    assert len(selected) == len(MESSAGES)


def test_select_relevant_messages_truncates():
    # Force a low token limit
    selected = cm.select_relevant_messages(MESSAGES, USER_INPUT, 5, "gpt-3.5-turbo")
    assert len(selected) < len(MESSAGES)


@pytest.mark.asyncio
async def test_condense_history_truncates():
    with patch("services.chat_service.context_module.llm_manager") as mock_llm_manager:
        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_llm.achat.return_value.response = "Summary of messages"
        mock_llm_manager.get_llm.return_value = mock_llm

        # Test with messages that should trigger summarization
        condensed = await cm.condense_history(MESSAGES, 5, "gpt-3.5-turbo")
        assert isinstance(condensed, str)
        assert len(condensed) > 0


@pytest.mark.asyncio
async def test_dynamic_context_selection():
    with patch("services.chat_service.context_module.llm_manager") as mock_llm_manager:
        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_llm.achat.return_value.response = "Summary of messages"
        mock_llm_manager.get_llm.return_value = mock_llm

        selected = await cm.dynamic_context_selection(
            MESSAGES, USER_INPUT, None, 1000, "gpt-3.5-turbo"
        )
        assert isinstance(selected, list)
        assert all(isinstance(m, dict) and "content" in m for m in selected)
