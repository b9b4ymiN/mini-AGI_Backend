"""
Ollama LLM integration for agent execution.
"""

from typing import List, Dict
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gpt-oss-20b"


def call_ollama(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Call Ollama chat API and return the assistant's response content.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (default: gpt-oss-20b)

    Returns:
        String content from assistant's response

    Raises:
        Exception: If HTTP request fails
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
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
            f"Failed to call Ollama at {OLLAMA_URL} with model {model}: {e}"
        )
    except (KeyError, TypeError) as e:
        raise Exception(
            f"Unexpected response structure from Ollama: {e}"
        )
