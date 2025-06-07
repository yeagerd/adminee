import pytest

from services.chat_service import context_module as cm

MESSAGES = [{"content": f"Message {i}"} for i in range(10)]
USER_INPUT = "What is the summary?"


def test_count_tokens():
    tokens = cm.count_tokens("hello world", model="gpt-3.5-turbo")
    assert isinstance(tokens, int)
    assert tokens > 0


def test_select_relevant_messages_fits():
    selected = cm.select_relevant_messages(MESSAGES, USER_INPUT, 1000)
    assert len(selected) == len(MESSAGES)


def test_select_relevant_messages_truncates():
    # Force a low token limit
    selected = cm.select_relevant_messages(MESSAGES, USER_INPUT, 5)
    assert len(selected) < len(MESSAGES)


def test_condense_history_truncates():
    condensed = cm.condense_history(MESSAGES, 5)
    assert isinstance(condensed, str)
    assert len(condensed) > 0


def test_dynamic_context_selection():
    selected = cm.dynamic_context_selection(MESSAGES, USER_INPUT, None, 1000)
    assert isinstance(selected, list)
    assert all("content" in m for m in selected)
