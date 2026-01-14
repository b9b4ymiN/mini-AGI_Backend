"""
Cached LLM wrapper with Redis caching.

Provides cached versions of LLM calls for improved performance.
"""

import json
import logging
from typing import List, Dict, Optional

from . import llm
from . import cache as cache_module
from .llm import LlmProviderError, MODEL_NAME, LLM_TEMPERATURE
from backend.logging_config import get_logger

logger = get_logger(__name__)


def get_messages_content(messages: List[Dict[str, str]]) -> tuple[str, str]:
    """
    Extract system instruction and prompt from messages list.

    Args:
        messages: List of message dictionaries

    Returns:
        Tuple of (system_instruction, prompt)
    """
    system_instruction = ""
    user_messages = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if isinstance(content, list):
            # Handle assistant-ui format: content is list of dicts
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    content = item.get("text", "")
                    break

        if role == "system":
            system_instruction = content
        elif role == "user":
            user_messages.append(content)

    # Combine user messages as prompt
    prompt = "\n".join(user_messages) if user_messages else ""

    return system_instruction, prompt


async def call_llm_cached(
    messages: List[Dict[str, str]],
    model: str = MODEL_NAME,
    persona: Optional[str] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> str:
    """
    Call LLM with caching support.

    Checks cache before making API call, stores result in cache after.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name
        persona: Optional persona ID for cache key
        use_cache: Whether to use cache (default: True)
        cache_ttl: Cache TTL in seconds (default: from config)

    Returns:
        String content from assistant's response

    Raises:
        LlmProviderError: If API call fails
    """
    # Extract system instruction and prompt
    system_instruction, prompt = get_messages_content(messages)

    # Try cache first
    if use_cache:
        cached_response = await cache_module.get_cached_llm_response(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model,
            persona=persona,
            temperature=LLM_TEMPERATURE
        )
        if cached_response is not None:
            logger.info("llm_cache_hit", model=model, persona=persona)
            return cached_response

    # Cache miss - call LLM
    logger.info("llm_cache_miss", model=model, persona=persona)
    response = llm.call_llm(messages, model)

    # Store in cache
    if use_cache:
        await cache_module.cache_llm_response(
            prompt=prompt,
            response=response,
            system_instruction=system_instruction,
            model=model,
            persona=persona,
            temperature=LLM_TEMPERATURE,
            ttl=cache_ttl
        )

    return response


# Export cached version as main interface
call_llm_async = call_llm_cached

# Sync wrapper for backward compatibility
def call_llm(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Synchronous wrapper for LLM calls (backward compatible).

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name

    Returns:
        String content from assistant's response
    """
    # Use original non-cached version for sync calls
    # (async caching requires async context)
    return llm.call_llm(messages, model)


# Re-export for backward compatibility
__all__ = [
    "call_llm_cached",
    "call_llm_async",
    "call_llm",
    "get_messages_content",
    "LlmProviderError",
    "MODEL_NAME",
    "LLM_TEMPERATURE",
]
