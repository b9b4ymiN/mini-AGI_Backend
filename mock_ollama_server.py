"""
Simple mock Ollama server for testing purposes.
This allows testing the backend without requiring actual Ollama installation.
"""

from fastapi import FastAPI, Request
from typing import List, Dict, Any
import json

app = FastAPI(title="Mock Ollama Server")


@app.get("/api/tags")
def list_tags():
    """Mock list of available models."""
    return {
        "models": [
            {
                "name": "gpt-oss-20b",
                "modified_at": "2024-01-15T10:00:00Z",
                "size": 12884901888
            }
        ]
    }


@app.post("/api/chat")
async def chat(request: Request):
    """
    Mock chat endpoint that returns simple JSON responses.
    Simulates an agent that follows the JSON protocol.
    """
    body = await request.json()
    messages = body.get("messages", [])

    # Get the last user message
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    # Generate a simple mock response based on the message
    response_content = generate_mock_response(user_message, messages)

    return {
        "model": "gpt-oss-20b",
        "created_at": "2024-01-15T10:30:00Z",
        "message": {
            "role": "assistant",
            "content": response_content
        },
        "done": True
    }


def generate_mock_response(user_message: str, messages: List[Dict[str, Any]]) -> str:
    """
    Generate a mock response that follows the agent JSON protocol.
    """
    # Check if this is from orchestrator (system message contains "Orchestrator")
    is_orchestrator = any("Orchestrator" in msg.get("content", "")
                         for msg in messages if msg.get("role") == "system")

    # Simple keyword-based responses
    user_lower = user_message.lower()

    # If asking to calculate or do math
    if any(word in user_lower for word in ["calculate", "compute", "math", "fibonacci", "sum"]):
        return json.dumps({
            "thought": "I should use the run_python tool to calculate this",
            "action": "use_tool",
            "tool": "run_python",
            "target_agent": None,
            "args": {"code": "result = sum(range(1, 11))\nprint(f'Sum: {result}')"},
            "answer": ""
        })

    # If asking to write code
    if any(word in user_lower for word in ["write code", "create function", "implement"]):
        return json.dumps({
            "thought": "This is a coding task, I should delegate to the coder agent",
            "action": "delegate",
            "tool": None,
            "target_agent": "coder",
            "args": {"task": user_message},
            "answer": ""
        })

    # If asking to read a file
    if "read" in user_lower and "file" in user_lower:
        return json.dumps({
            "thought": "I should read the requested file",
            "action": "use_tool",
            "tool": "read_file",
            "target_agent": None,
            "args": {"path": "README.md"},
            "answer": ""
        })

    # If this is a tool result (contains "Tool" and "output")
    if "tool" in user_lower and "output" in user_lower:
        return json.dumps({
            "thought": "The tool executed successfully, I can now provide the final answer",
            "action": "final",
            "tool": None,
            "target_agent": None,
            "args": {},
            "answer": "I've successfully executed the requested operation. The tool completed without errors."
        })

    # Default: provide a simple final answer
    return json.dumps({
        "thought": "This is a simple query, I can answer directly",
        "action": "final",
        "tool": None,
        "target_agent": None,
        "args": {},
        "answer": f"Mock response: I received your message '{user_message[:50]}...' and I'm a mock Ollama server. In production, a real LLM would provide intelligent responses here."
    })


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Mock Ollama Server - Use /api/chat for chat completions"}


if __name__ == "__main__":
    import uvicorn
    print("Starting Mock Ollama Server on port 11434...")
    print("This simulates Ollama for testing without requiring actual installation.")
    uvicorn.run(app, host="127.0.0.1", port=11434)
