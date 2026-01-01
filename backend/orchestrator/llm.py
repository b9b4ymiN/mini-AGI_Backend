"""
Multi-provider LLM integration for agent execution.
Supports: Ollama, Z.AI

Configuration via environment variables:
- LLM_PROVIDER: "ollama" or "zai" (default: "ollama")
- LLM_MODEL: Model name (default depends on provider)
- LLM_TEMPERATURE: Temperature 0.0-1.0 (default: 0.2)
- LLM_MAX_TOKENS: Max output tokens for providers that support it (default: 2000)
- OLLAMA_URL: Ollama base URL (default: "http://localhost:11434")
- ZAI_API_KEY: Z.AI API key (required if using Z.AI)
- ZAI_BASE_URL: Z.AI base URL (default: "https://api.z.ai/api/coding/paas/v4")
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Dict, List, Optional, Tuple

import requests

# ============================================================================
# Configuration
# ============================================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL = "gpt-oss-20b"

# Z.AI configuration
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
ZAI_DEFAULT_MODEL = "glm-4.6"

# Determine model based on provider
if LLM_PROVIDER == "zai":
    MODEL_NAME = os.getenv("LLM_MODEL", ZAI_DEFAULT_MODEL)
else:
    MODEL_NAME = os.getenv("LLM_MODEL", OLLAMA_DEFAULT_MODEL)


# ============================================================================
# HTTP Client (reuse connections) + Retry helper
# ============================================================================

_SESSION = requests.Session()

_RETRY_STATUS = {429, 500, 502, 503, 504}


class LlmProviderError(Exception):
    """Raised when an LLM provider call fails."""


def _sleep_backoff(attempt: int, retry_after: Optional[str] = None) -> None:
    """Exponential backoff with jitter, honoring Retry-After when present."""
    if retry_after:
        try:
            time.sleep(float(retry_after))
            return
        except ValueError:
            pass

    base = min(2**attempt, 20)
    jitter = random.uniform(0, 0.5)
    time.sleep(base + jitter)


def _post_with_retry(
    *,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_payload: Optional[Dict] = None,
    timeout: Tuple[float, float] = (10.0, 300.0),
    max_retries: int = 4,
) -> requests.Response:
    """POST with retries on transient errors and rate limits."""
    last_err: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = _SESSION.post(url, headers=headers, json=json_payload, timeout=timeout)

            
            # Retryable statuses
            if resp.status_code in _RETRY_STATUS:
                retry_after = resp.headers.get("Retry-After")
                snippet = (resp.text or "")[:800]
                last_err = LlmProviderError(
                    f"HTTP {resp.status_code}. "
                    f"{('Retry-After=' + retry_after + '. ') if retry_after else ''}"
                    f"Body (first 800 chars): {snippet}"
                )
                if attempt < max_retries:
                    _sleep_backoff(attempt, retry_after)
                    continue
                raise last_err

            # For non-retryable errors (like 400), raise with body too
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                snippet = (resp.text or "")[:2000]
                raise LlmProviderError(
                    f"HTTP {resp.status_code} calling {url}. "
                    f"Body (first 2000 chars): {snippet}"
                ) from e

            return resp

        except requests.exceptions.Timeout as e:
            last_err = e
            if attempt < max_retries:
                _sleep_backoff(attempt)
                continue
            raise LlmProviderError(f"Timeout calling {url}: {e}") from e

        except requests.exceptions.RequestException as e:
            last_err = e
            if attempt < max_retries:
                _sleep_backoff(attempt)
                continue
            raise LlmProviderError(f"Failed to call {url}: {e}") from e

    raise LlmProviderError(f"Failed to call {url}: {last_err}")


# ============================================================================
# Provider Implementations
# ============================================================================

def call_ollama(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Call Ollama chat API and return the assistant's response content.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (default from config)

    Returns:
        String content from assistant's response

    Raises:
        Exception: If HTTP request fails
    """
    url = f"{OLLAMA_URL}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE,
        },
    }

    try:
        response = _post_with_retry(
            url=url,
            json_payload=payload,
            timeout=(5.0, 60.0),
            max_retries=2,
        )
        data = response.json()

        # Expected structure:
        # {
        #   "message": {
        #     "role": "assistant",
        #     "content": "..."
        #   }
        # }
        return data["message"]["content"]

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise LlmProviderError(
            f"Unexpected response structure from Ollama at {url} with model {model}: {e}"
        ) from e

def call_zai(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    if not ZAI_API_KEY:
        raise LlmProviderError(
            "ZAI_API_KEY environment variable is required for Z.AI provider. "
            "Set it in .env file or environment."
        )

    url = f"{ZAI_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {ZAI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # --- Normalize model (สำคัญมาก) ---
    model_norm = (model or "").strip()
    if model_norm:
        model_norm = model_norm.lower()  # "glm-4.6" ต้องเป็น lowercase บ่อยครั้ง

    # --- Validate messages (กัน 400 จาก content type) ---
    cleaned_msgs: List[Dict[str, str]] = []
    allowed_roles = {"system", "user", "assistant", "tool"}
    for i, m in enumerate(messages or []):
        role = (m.get("role") or "").strip()
        content = m.get("content")

        if role not in allowed_roles:
            raise LlmProviderError(f"Invalid message role at index {i}: {role}")

        if not isinstance(content, str):
            # ถ้ามี dict/list/None หลุดมา จะทำให้ API 400 ได้
            raise LlmProviderError(
                f"Invalid message content type at index {i}: {type(content).__name__} (must be str)"
            )

        cleaned_msgs.append({"role": role, "content": content})

    # --- Clamp temperature ---
    temp = float(LLM_TEMPERATURE)
    if temp < 0.0:
        temp = 0.0
    if temp > 1.0:
        temp = 1.0

    payload = {
        "model": model_norm or ZAI_DEFAULT_MODEL,
        "messages": cleaned_msgs,
        "max_tokens": int(LLM_MAX_TOKENS),
        "temperature": temp,
        # Z.ai supports "thinking" parameter; disable for speed
        "thinking": {"type": "disabled"},
        # ถ้าต้องการ stream ในอนาคตค่อยเปิด:
        # "stream": False,
    }

    response = _post_with_retry(
        url=url,
        headers=headers,
        json_payload=payload,
        timeout=(10.0, 300.0),
        max_retries=2,  # 400 ไม่ต้อง retry; 429/5xx helper จะจัดเอง
    )

    try:
        data = response.json()
        choice0 = data["choices"][0]
        msg = choice0.get("message") or {}
        content = (msg.get("content") or "").strip()

        # fallback เผื่อบางรูปแบบ
        if not content:
            content = (choice0.get("text") or "").strip()

        return content

    except (json.JSONDecodeError, KeyError, TypeError, IndexError) as e:
        raise LlmProviderError(
            f"Unexpected response structure from Z.AI at {url} with model {payload['model']}: {e}"
        ) from e


# ============================================================================
# Unified Interface
# ============================================================================

def call_llm(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Call the configured LLM provider and return the assistant's response.

    This is the main entry point that routes to the appropriate provider.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (uses configured default if not specified)

    Returns:
        String content from assistant's response

    Raises:
        Exception: If provider is unknown or API call fails
    """
    if LLM_PROVIDER == "zai":
        return call_zai(messages, model)
    elif LLM_PROVIDER == "ollama":
        return call_ollama(messages, model)
    else:
        raise LlmProviderError(
            f"Unknown LLM provider: {LLM_PROVIDER}. "
            f"Supported providers: 'ollama', 'zai'"
        )


# ============================================================================
# Provider Info (for debugging/logging)
# ============================================================================

def get_provider_info() -> Dict[str, str]:
    """Get current LLM provider configuration."""
    return {
        "provider": LLM_PROVIDER,
        "model": MODEL_NAME,
        "temperature": str(LLM_TEMPERATURE),
        "ollama_url": OLLAMA_URL if LLM_PROVIDER == "ollama" else "N/A",
        "zai_url": ZAI_BASE_URL if LLM_PROVIDER == "zai" else "N/A",
        "zai_api_key_set": "Yes" if ZAI_API_KEY else "No",
    }
