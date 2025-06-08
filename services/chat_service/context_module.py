"""
Context condensation and selection module for chat_service.
Implements OpenHands Context Condensation strategy.
"""

import logging
from typing import Any, Dict, List, Optional

import tiktoken

from .llm_manager import llm_manager

logger = logging.getLogger(__name__)

# 7.1 Define context condensation strategy based on OpenHands Context Condensation
# - Select relevant messages and data from thread history and external sources
# - Summarize or condense long histories to fit a requested token size for a specified llm model
# - Support dynamic context selection based on user input and thread state

# add a python logger and log when condense_history happens (before num messages, before tokens, after num messages, after tokens). Also, temporarily, log the llm summary


def count_tokens(text: str, model: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except (KeyError, ValueError):
        # Fallback to a common encoding if model not found or invalid
        enc = tiktoken.get_encoding("cl100k_base")
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


async def condense_history(
    messages: List[Dict[str, Any]], max_tokens: int, model: str, **llm_kwargs
) -> str:
    """
    Condense message history using LLM summarization.

    Args:
        messages: List of message dictionaries
        max_tokens: Maximum number of tokens for the summary
        model: Model to use for summarization
        **llm_kwargs: Additional arguments to pass to the LLM

    Returns:
        Condensed summary of the messages
    """
    logger.info(f"Condensing {len(messages)} messages for model {model}")

    # If no messages, return empty string
    if not messages:
        return ""

    # If only one message, return it as is if it fits
    if len(messages) == 1:
        single_msg = messages[0].get("content", "")
        if count_tokens(single_msg, model) <= max_tokens:
            return single_msg

    # Prepare messages for summarization
    system_prompt = """You are a helpful assistant that summarizes conversation history. 
    Create a concise summary that captures the key points and maintains the context 
    of the conversation. Focus on the most important information."""

    # Format messages for the LLM
    formatted_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Please summarize the following conversation in {max_tokens} tokens or less:\n\n",
        },
    ]

    # Add conversation history
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        formatted_messages.append({"role": role, "content": content})

    try:
        # Get LLM instance with the specified model
        llm = llm_manager.get_llm(model=model, **llm_kwargs)

        # Call the LLM for summarization
        response = await llm.achat(messages=formatted_messages)
        summary = response.response

        # Ensure the summary doesn't exceed the token limit
        summary_tokens = count_tokens(summary, model)
        if summary_tokens > max_tokens:
            # If summary is too long, truncate it
            tokens = tiktoken.encoding_for_model(model).encode(summary)
            summary = tiktoken.encoding_for_model(model).decode(tokens[:max_tokens])

        logger.info(f"Generated summary of {summary_tokens} tokens")
        return summary

    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        # Fallback to naive concatenation if summarization fails
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


async def dynamic_context_selection(
    messages: List[Dict[str, Any]],
    user_input: str,
    thread_state: Optional[Dict[str, Any]],
    max_tokens: int,
    model: str,
    **llm_kwargs,
) -> List[Dict[str, Any]]:
    # Placeholder: could use thread_state to bias selection
    return select_relevant_messages(messages, user_input, max_tokens, model)
