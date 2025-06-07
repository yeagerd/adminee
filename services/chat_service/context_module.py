"""
Context condensation and selection module for chat_service.
Implements OpenHands Context Condensation strategy.
"""
from typing import List, Dict, Any, Optional
import tiktoken

# 7.1 Define context condensation strategy based on OpenHands Context Condensation
# - Select relevant messages and data from thread history and external sources
# - Summarize or condense long histories to fit a requested token size for a specified llm model
# - Support dynamic context selection based on user input and thread state

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def select_relevant_messages(messages: List[Dict[str, Any]], user_input: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> List[Dict[str, Any]]:
    # Naive: select most recent messages that fit in max_tokens
    selected = []
    total_tokens = count_tokens(user_input, model)
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg.get("content", ""), model)
        if total_tokens + msg_tokens > max_tokens:
            break
        selected.insert(0, msg)
        total_tokens += msg_tokens
    return selected

def condense_history(messages: List[Dict[str, Any]], max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
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

def dynamic_context_selection(messages: List[Dict[str, Any]], user_input: str, thread_state: Optional[Dict[str, Any]], max_tokens: int, model: str = "gpt-3.5-turbo") -> List[Dict[str, Any]]:
    # Placeholder: could use thread_state to bias selection
    return select_relevant_messages(messages, user_input, max_tokens, model)
