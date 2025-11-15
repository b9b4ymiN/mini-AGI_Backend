"""
FastAPI application for Mini-AGI Backend.
Main entry point for the orchestration system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator.models import ChatRequest, ChatResponse
from .orchestrator.core import orchestrate

app = FastAPI(
    title="Mini-AGI Backend",
    description="Agent orchestration with Ollama + MCP",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Expects assistant-ui message format:
    {
      "messages": [
        {
          "role": "user",
          "content": [{"type": "text", "text": "..."}]
        }
      ]
    }
    """
    # Extract latest user message
    last_user_msg = ""

    for msg in reversed(req.messages):
        if msg.get("role") == "user":
            content = msg.get("content", [])

            if content and isinstance(content, list):
                first_item = content[0]

                if isinstance(first_item, dict) and first_item.get("type") == "text":
                    last_user_msg = first_item.get("text", "")
                    break

    if not last_user_msg:
        last_user_msg = "No text content provided."

    # Run orchestration
    answer, events = orchestrate(last_user_msg)

    return ChatResponse(answer=answer, events=events)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
