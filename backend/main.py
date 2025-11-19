"""
FastAPI application for Mini-AGI Backend.
Main entry point for the orchestration system.
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator.models import ChatRequest, ChatResponse
from .orchestrator.core import orchestrate
from .orchestrator.llm import get_provider_info
from .orchestrator.personas import get_persona_or_custom, get_available_personas

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
      "persona": "oi-trader",  // Optional: Load predefined persona
      "messages": [
        {
          "role": "system",
          "content": [{"type": "text", "text": "Custom system instructions..."}]
        },
        {
          "role": "user",
          "content": [{"type": "text", "text": "..."}]
        }
      ]
    }

    Persona takes priority over system messages in the messages array.
    If no persona is specified, falls back to system message from messages array.
    """
    # Extract system message from messages array (optional)
    custom_system_instruction = ""

    for msg in req.messages:
        if msg.get("role") == "system":
            content = msg.get("content", [])

            if content and isinstance(content, list):
                first_item = content[0]

                if isinstance(first_item, dict) and first_item.get("type") == "text":
                    custom_system_instruction = first_item.get("text", "")
                    break
            elif isinstance(content, str):
                # Support simple string format
                custom_system_instruction = content
                break

    # Get system instruction from persona or custom (persona takes priority)
    system_instruction = get_persona_or_custom(
        persona_id=req.persona,
        custom_instruction=custom_system_instruction
    )

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
            elif isinstance(content, str):
                # Support simple string format
                last_user_msg = content
                break

    if not last_user_msg:
        last_user_msg = "No text content provided."

    # Run orchestration with optional system instruction
    answer, events = orchestrate(last_user_msg, system_instruction=system_instruction)

    return ChatResponse(answer=answer, events=events)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/llm/info")
def llm_info():
    """Get current LLM provider configuration."""
    return get_provider_info()


@app.get("/personas")
def list_personas():
    """
    Get list of available personas.

    Returns:
        List of persona objects with id, name, file, and exists status
    """
    return {"personas": get_available_personas()}
