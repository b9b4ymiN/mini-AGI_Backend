"""
FastAPI application for Mini-AGI Backend.
Main entry point for the orchestration system.
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator.models import ChatRequest, ChatResponse
from .orchestrator.core import orchestrate
from .orchestrator.llm import get_provider_info
from .orchestrator.personas import get_persona_or_custom, get_available_personas
from .orchestrator import memory, db_management

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

    # Run orchestration with memory and optional system instruction
    answer, events, session_id, context_used = orchestrate(
        user_input=last_user_msg,
        system_instruction=system_instruction,
        session_id=req.session_id,
        user_id=req.user_id,
        persona=req.persona
    )

    return ChatResponse(
        answer=answer,
        events=events,
        session_id=session_id,
        context_used=context_used
    )


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


# =============================================================================
# Memory Management Endpoints
# =============================================================================

@app.post("/sessions")
def create_new_session(user_id: str = None):
    """
    Create a new conversation session.

    Args:
        user_id: Optional user identifier

    Returns:
        New session ID
    """
    session_id = memory.create_session(user_id)
    return {"session_id": session_id}


@app.get("/sessions/{session_id}")
def get_session_info(session_id: str):
    """
    Get information about a session.

    Args:
        session_id: Session identifier

    Returns:
        Session statistics and metadata
    """
    stats = memory.get_session_stats(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats


@app.get("/sessions/{session_id}/history")
def get_session_history(session_id: str, limit: int = 10):
    """
    Get conversation history for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages (default: 10)

    Returns:
        List of conversation turns
    """
    history = memory.get_conversation_history(session_id, limit=limit, include_metadata=True)
    return {"session_id": session_id, "history": history, "count": len(history)}


@app.get("/conversations/search")
def search_conversation_history(
    query: str,
    user_id: str = None,
    session_id: str = None,
    limit: int = 5
):
    """
    Search conversations by text content.

    Args:
        query: Search query
        user_id: Optional filter by user
        session_id: Optional filter by session
        limit: Maximum results (default: 5)

    Returns:
        List of matching conversations
    """
    results = memory.search_conversations(query, user_id, session_id, limit)
    return {"query": query, "results": results, "count": len(results)}


@app.post("/memory/facts")
def save_user_fact(
    fact_key: str,
    fact_value: str,
    fact_type: str = "general",
    user_id: str = None,
    session_id: str = None,
    confidence: float = 1.0
):
    """
    Save a learned fact about the user.

    Args:
        fact_key: Unique key for the fact
        fact_value: The fact content
        fact_type: Type of fact (preference, skill, etc.)
        user_id: Optional user identifier
        session_id: Source session
        confidence: Confidence level (0.0 - 1.0)

    Returns:
        Success message
    """
    memory.save_memory_fact(
        fact_key=fact_key,
        fact_value=fact_value,
        fact_type=fact_type,
        user_id=user_id,
        session_id=session_id,
        confidence=confidence
    )
    return {"status": "success", "message": "Fact saved"}


@app.get("/memory/facts")
def get_user_facts(user_id: str = None, fact_type: str = None):
    """
    Get saved facts about a user.

    Args:
        user_id: Optional filter by user
        fact_type: Optional filter by type

    Returns:
        List of memory facts
    """
    facts = memory.get_memory_facts(user_id, fact_type)
    return {"facts": facts, "count": len(facts)}


@app.delete("/sessions/cleanup")
def cleanup_old_sessions_endpoint(days: int = 30):
    """
    Delete sessions older than specified days.

    Args:
        days: Age threshold in days (default: 30)

    Returns:
        Number of sessions deleted
    """
    deleted = memory.cleanup_old_sessions(days)
    return {"deleted_count": deleted, "days": days}


# =============================================================================
# Database Management Endpoints (For Oracle Cloud Free Tier)
# =============================================================================

@app.get("/db/size")
def get_database_size():
    """
    Get current database size and usage percentage.

    Returns:
        Database size in MB, max size, and usage percentage
    """
    return db_management.get_db_size()


@app.get("/db/stats")
def get_database_stats():
    """
    Get detailed database statistics.

    Returns:
        Comprehensive database statistics including row counts and size info
    """
    return db_management.get_db_stats()


@app.get("/db/status")
def check_database_status():
    """
    Check if database is approaching or exceeding size limits.

    Returns:
        Status (ok/warning/critical) and recommended actions
    """
    return db_management.check_size_limits()


@app.post("/db/cleanup/auto")
def auto_cleanup():
    """
    Automatically cleanup old data if approaching size limits.

    Performs aggressive cleanup if critical, normal cleanup if warning.

    Returns:
        Cleanup results including deleted counts and new size
    """
    return db_management.auto_cleanup_if_needed()


@app.post("/db/archive")
def archive_conversations(days: int = 90, compress: bool = True):
    """
    Archive old conversations to compressed file.

    Args:
        days: Archive conversations older than this many days (default: 90)
        compress: Use gzip compression (default: True)

    Returns:
        Archive results including file path and statistics
    """
    result = db_management.archive_old_conversations(days, compress)
    return result


@app.post("/db/vacuum")
def vacuum_database():
    """
    Reclaim unused space in database.

    Runs VACUUM to compact the database file.

    Returns:
        Size before and after vacuum operation
    """
    return db_management.vacuum_database()


@app.post("/db/optimize")
def optimize_database():
    """
    Optimize database for better performance.

    Runs VACUUM, ANALYZE, and REINDEX operations.

    Returns:
        Optimization results and statistics
    """
    return db_management.optimize_database()


@app.get("/db/recommendations")
def get_storage_recommendations():
    """
    Get storage management recommendations.

    Analyzes current database state and provides actionable recommendations.

    Returns:
        List of recommendations based on current usage
    """
    return db_management.get_storage_recommendations()
