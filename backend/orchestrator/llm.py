"""
Multi-provider LLM integration for agent execution.
Supports: Ollama, Z.AI

Configuration via environment variables:
- LLM_PROVIDER: "ollama" or "zai" (default: "ollama")
- LLM_MODEL: Model name (default depends on provider)
- LLM_TEMPERATURE: Temperature 0.0-1.0 (default: 0.2)
- OLLAMA_URL: Ollama base URL (default: "http://localhost:11434")
- ZAI_API_KEY: Z.AI API key (required if using Z.AI)
- ZAI_BASE_URL: Z.AI base URL (default: "https://api.z.ai/api/coding/paas/v4")
"""

from typing import List, Dict
import requests
import os

# ============================================================================
# Configuration
# ============================================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

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
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE,
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Expected structure:
        # {
        #   "message": {
        #     "role": "assistant",
        #     "content": "..."
        #   }
        # }
        return data["message"]["content"]

    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to call Ollama at {url} with model {model}: {e}"
        )
    except (KeyError, TypeError) as e:
        raise Exception(
            f"Unexpected response structure from Ollama: {e}"
        )


def call_zai(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Call Z.AI chat API and return the assistant's response content.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (default from config)

    Returns:
        String content from assistant's response

    Raises:
        Exception: If HTTP request fails or API key missing
    """
    if not ZAI_API_KEY:
        raise Exception(
            "ZAI_API_KEY environment variable is required for Z.AI provider. "
            "Set it in .env file or environment."
        )

    url = f"{ZAI_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {ZAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "reasoning": {"include_reasoning": False},
        "messages": messages,
        "max_tokens": 10240,
        "temperature": LLM_TEMPERATURE,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Expected structure:
        # {
        #   "choices": [
        #     {
        #       "message": {
        #         "content": "...",
        #         "role": "assistant"
        #       }
        #     }
        #   ]
        # }
        content = data["choices"][0]["message"]["content"]

        # Fallback to reasoning_content if content is empty
        if not content or not content.strip():
            content = data["choices"][0]["message"].get("reasoning_content", "")

        return content

    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to call Z.AI at {url} with model {model}: {e}"
        )
    except (KeyError, TypeError, IndexError) as e:
        raise Exception(
            f"Unexpected response structure from Z.AI: {e}"
        )


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
        raise Exception(
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
