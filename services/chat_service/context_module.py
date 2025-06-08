"""
Context condensation and selection module for chat_service.
Implements OpenHands Context Condensation strategy.
"""

from typing import Any, Dict, List, Optional

import tiktoken

# 7.1 Define context condensation strategy based on OpenHands Context Condensation
# - Select relevant messages and data from thread history and external sources
# - Summarize or condense long histories to fit a requested token size for a specified llm model
# - Support dynamic context selection based on user input and thread state

# add a python logger and log when condense_history happens (before num messages, before tokens, after num messages, after tokens). Also, temporarily, log the llm summary


def count_tokens(text: str, model: str) -> int:
    if not model:
        model = "gpt-4.1-nano"
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def select_relevant_messages(
    messages: List[Dict[str, Any]],
    user_input: str,
    max_tokens: int,
    model: str,
) -> List[Dict[str, Any]]:
    # Naive: select most recent messages that fit in max_tokens
    selected: List[Dict[str, Any]] = []
    total_tokens = count_tokens(user_input, model)
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg.get("content", ""), model)
        if total_tokens + msg_tokens > max_tokens:
            break
        selected.insert(0, msg)
        total_tokens += msg_tokens
    return selected


def condense_history(
    messages: List[Dict[str, Any]], max_tokens: int, model: str
) -> str:
    # Naive: concatenate and truncate
    result = ""
    total_tokens = 0
    for msg in reversed(messages):
        msg_text = msg.get("content", "")
        msg_tokens = count_tokens(msg_text, model)
        if total_tokens + msg_tokens > max_tokens:
            break
        result = msg_text + "\n" + result
        total_tokens += msg_tokens
    return result.strip()


def dynamic_context_selection(
    messages: List[Dict[str, Any]],
    user_input: str,
    thread_state: Optional[Dict[str, Any]],
    max_tokens: int,
    model: str,
) -> List[Dict[str, Any]]:
    # Placeholder: could use thread_state to bias selection
    return select_relevant_messages(messages, user_input, max_tokens, model)
