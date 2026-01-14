"""
API v1 endpoints.

Version 1 of the API includes all original endpoints with versioned paths.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.orchestrator.models import ChatRequest, ChatResponse
from backend.orchestrator.core import orchestrate
from backend.orchestrator.llm import get_provider_info, LlmProviderError
from backend.orchestrator.personas import get_persona_or_custom, get_available_personas
from backend.orchestrator import memory, db_management
from backend.security import verify_api_key, require_admin, SecurityConfig
from backend.logging_config import get_logger
from backend.api.pagination import (
    PaginationParams,
    PaginatedResponse,
    get_pagination_params,
    paginate
)
from backend.database.repository import ConversationRepository
from backend.database import get_db_session, _async_session_maker
from backend.monitoring import (
    WebhookEvent,
    Webhook,
    get_webhook_manager
)

logger = get_logger(__name__)

# Create API router for v1
router = APIRouter(prefix="/v1", tags=["v1"])


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
def chat_v1(req: ChatRequest, _auth: str = Depends(verify_api_key)) -> ChatResponse:
    """
    Main chat endpoint (v1).

    Expects assistant-ui message format.
    Requires authentication via X-API-Key header.

    **API Version:** v1
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
    try:
        answer, events, session_id, context_used = orchestrate(
            user_input=last_user_msg,
            system_instruction=system_instruction,
            session_id=req.session_id,
            user_id=req.user_id,
            persona=req.persona
        )

        # Ensure answer is a string (defensive: avoid type issues)
        if not isinstance(answer, str):
            answer = str(answer)

        response = ChatResponse(
            answer=answer,
            events=events,
            session_id=session_id,
            context_used=context_used
        )

        # Log response before returning (for debugging)
        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
        logger.info(
            "v1_chat_response",
            session_id=session_id,
            context_used=context_used,
            answer_preview=answer_preview
        )

        return response

    except LlmProviderError as e:
        # Return user-friendly error message from the exception
        response = ChatResponse(
            answer=e.user_message,
            events=[],
            session_id=req.session_id or "",
            context_used=False
        )
        logger.error("v1_llm_error", error=str(e))
        return response

    except Exception as e:
        # Catch-all for unexpected errors - return as JSON instead of crashing
        response = ChatResponse(
            answer=f"An error occurred: {str(e)}",
            events=[],
            session_id=req.session_id or "",
            context_used=False
        )
        logger.error("v1_unexpected_error", error=str(e))
        return response


# =============================================================================
# Personas Endpoints
# =============================================================================

@router.get("/personas")
def list_personas_v1(_auth: str = Depends(verify_api_key)):
    """
    Get list of available personas (v1).

    Returns:
        List of persona objects with id, name, file, and exists status

    **API Version:** v1
    """
    return {"personas": get_available_personas()}


# =============================================================================
# Memory Management Endpoints
# =============================================================================

@router.post("/sessions")
def create_new_session_v1(user_id: str = None, _auth: str = Depends(verify_api_key)):
    """
    Create a new conversation session (v1).

    Args:
        user_id: Optional user identifier

    Returns:
        New session ID

    **API Version:** v1
    """
    session_id = memory.create_session(user_id)
    return {"session_id": session_id}


@router.get("/sessions", response_model=PaginatedResponse)
def list_sessions_v1(
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: str = None,
    _auth: str = Depends(verify_api_key)
):
    """
    List sessions with pagination (v1).

    Args:
        pagination: Pagination parameters
        user_id: Optional filter by user ID

    Returns:
        Paginated list of sessions

    **API Version:** v1
    """
    from backend.database.repository import ConversationRepository

    async def _get_sessions():
        async with get_db_session() as db:
            repo = ConversationRepository(db)

            # Build query
            from sqlalchemy import select, func
            from backend.database.models import Session

            query = select(Session).order_by(Session.created_at.desc())

            # Filter by user_id if provided
            if user_id:
                query = query.where(Session.user_id == user_id)

            # Get total count
            from backend.database import _async_session_maker
            async with _async_session_maker() as count_session:
                count_query = select(func.count()).select_from(query.subquery())
                count_result = await count_session.execute(count_query)
                total = count_result.scalar() or 0

            # Apply pagination
            offset = (pagination.page - 1) * pagination.page_size
            query = query.offset(offset).limit(pagination.page_size)

            result = await db.execute(query)
            sessions = result.scalars().all()

            items = [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "last_active": s.last_active.isoformat() if s.last_active else None,
                    "message_count": s.message_count if hasattr(s, "message_count") else 0,
                }
                for s in sessions
            ]

            return paginate(items, total, pagination)

    import asyncio
    return asyncio.run(_get_sessions())


@router.get("/sessions/{session_id}")
def get_session_info_v1(session_id: str, _auth: str = Depends(verify_api_key)):
    """
    Get information about a session (v1).

    Args:
        session_id: Session identifier

    Returns:
        Session statistics and metadata

    **API Version:** v1
    """
    stats = memory.get_session_stats(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats


@router.get("/sessions/{session_id}/history")
def get_session_history_v1(session_id: str, limit: int = 10, _auth: str = Depends(verify_api_key)):
    """
    Get conversation history for a session (v1).

    Args:
        session_id: Session identifier
        limit: Maximum number of messages (default: 10)

    Returns:
        List of conversation turns

    **API Version:** v1
    """
    history = memory.get_conversation_history(session_id, limit=limit, include_metadata=True)
    return {"session_id": session_id, "history": history, "count": len(history)}


@router.get("/conversations/search")
def search_conversation_history_v1(
    query: str,
    user_id: str = None,
    session_id: str = None,
    limit: int = 5,
    _auth: str = Depends(verify_api_key)
):
    """
    Search conversations by text content (v1).

    Args:
        query: Search query
        user_id: Optional filter by user
        session_id: Optional filter by session
        limit: Maximum results (default: 5)

    Returns:
        List of matching conversations

    **API Version:** v1
    """
    results = memory.search_conversations(query, user_id, session_id, limit)
    return {"query": query, "results": results, "count": len(results)}


@router.post("/memory/facts")
def save_user_fact_v1(
    fact_key: str,
    fact_value: str,
    fact_type: str = "general",
    user_id: str = None,
    session_id: str = None,
    confidence: float = 1.0,
    _auth: str = Depends(verify_api_key)
):
    """
    Save a learned fact about the user (v1).

    Args:
        fact_key: Unique key for the fact
        fact_value: The fact content
        fact_type: Type of fact (preference, skill, etc.)
        user_id: Optional user identifier
        session_id: Source session
        confidence: Confidence level (0.0 - 1.0)

    Returns:
        Success message

    **API Version:** v1
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


@router.get("/memory/facts")
def get_user_facts_v1(user_id: str = None, fact_type: str = None, _auth: str = Depends(verify_api_key)):
    """
    Get saved facts about a user (v1).

    Args:
        user_id: Optional filter by user
        fact_type: Optional filter by type

    Returns:
        List of memory facts

    **API Version:** v1
    """
    facts = memory.get_memory_facts(user_id, fact_type)
    return {"facts": facts, "count": len(facts)}


@router.delete("/sessions/cleanup")
def cleanup_old_sessions_v1(days: int = 30, _auth: str = Depends(verify_api_key)):
    """
    Delete sessions older than specified days (v1).

    Args:
        days: Age threshold in days (default: 30)

    Returns:
        Number of sessions deleted

    **API Version:** v1
    """
    deleted = memory.cleanup_old_sessions(days)
    return {"deleted_count": deleted, "days": days}


# =============================================================================
# Database Management Endpoints (Admin Only)
# =============================================================================

@router.get("/db/size")
def get_database_size_v1(_admin: str = Depends(require_admin)):
    """
    Get current database size and usage percentage (v1).

    Returns:
        Database size in MB, max size, and usage percentage

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.get_db_size()


@router.get("/db/stats")
def get_database_stats_v1(_admin: str = Depends(require_admin)):
    """
    Get detailed database statistics (v1).

    Returns:
        Comprehensive database statistics including row counts and size info

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.get_db_stats()


@router.get("/db/status")
def check_database_status_v1(_admin: str = Depends(require_admin)):
    """
    Check if database is approaching or exceeding size limits (v1).

    Returns:
        Status (ok/warning/critical) and recommended actions

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.check_size_limits()


@router.post("/db/cleanup/auto")
def auto_cleanup_v1(_admin: str = Depends(require_admin)):
    """
    Automatically cleanup old data if approaching size limits (v1).

    Performs aggressive cleanup if critical, normal cleanup if warning.

    Returns:
        Cleanup results including deleted counts and new size

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.auto_cleanup_if_needed()


@router.post("/db/archive")
def archive_conversations_v1(days: int = 90, compress: bool = True, _admin: str = Depends(require_admin)):
    """
    Archive old conversations to compressed file (v1).

    Args:
        days: Archive conversations older than this many days (default: 90)
        compress: Use gzip compression (default: True)

    Returns:
        Archive results including file path and statistics

    **API Version:** v1
    **Admin Only:** Yes
    """
    result = db_management.archive_old_conversations(days, compress)
    return result


@router.post("/db/vacuum")
def vacuum_database_v1(_admin: str = Depends(require_admin)):
    """
    Reclaim unused space in database (v1).

    Runs VACUUM to compact the database file.

    Returns:
        Size before and after vacuum operation

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.vacuum_database()


@router.post("/db/optimize")
def optimize_database_v1(_admin: str = Depends(require_admin)):
    """
    Optimize database for better performance (v1).

    Runs VACUUM, ANALYZE, and REINDEX operations.

    Returns:
        Optimization results and statistics

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.optimize_database()


@router.get("/db/recommendations")
def get_storage_recommendations_v1(_admin: str = Depends(require_admin)):
    """
    Get storage management recommendations (v1).

    Analyzes current database state and provides actionable recommendations.

    Returns:
        List of recommendations based on current usage

    **API Version:** v1
    **Admin Only:** Yes
    """
    return db_management.get_storage_recommendations()
