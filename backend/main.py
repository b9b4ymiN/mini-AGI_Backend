"""
FastAPI application for Mini-AGI Backend.
Main entry point for the orchestration system.
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .orchestrator.models import ChatRequest, ChatResponse
from .orchestrator.core import orchestrate
from .orchestrator.llm import get_provider_info, LlmProviderError
from .orchestrator.personas import get_persona_or_custom, get_available_personas
from .orchestrator import memory, db_management
from .security import (
    verify_api_key,
    SecurityConfig,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
    AuditLoggingMiddleware,
    require_admin,
)
from .logging_config import configure_logging, get_logger, RequestIDMiddleware
from .api import v1 as api_v1
from .monitoring import init_telemetry, shutdown_telemetry, MonitoringMiddleware, CompressionMiddleware
from .analytics import AnalyticsMiddleware
from .errors import register_exception_handlers

# Configure structured logging
configure_logging()
logger = get_logger(__name__)


# =============================================================================
# Lifespan Context Manager
# =============================================================================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    init_telemetry(
        service_name="mini-agi-backend",
        service_version="1.0.0",
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        enable_console_export=os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
        enable_prometheus=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
        prometheus_port=int(os.getenv("PROMETHEUS_PORT", "8000")),
    )
    logger.info("application_started", version="1.0.0")

    yield

    # Shutdown
    shutdown_telemetry()
    logger.info("application_shutdown")


app = FastAPI(
    title="Mini-AGI Backend",
    description="Agent orchestration with Ollama + MCP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register exception handlers
register_exception_handlers(app)


# =============================================================================
# Middleware (order matters!)
# =============================================================================

# 1. Request ID (must be first for distributed tracing)
app.add_middleware(RequestIDMiddleware)

# 2. Monitoring (collect metrics for all requests)
app.add_middleware(MonitoringMiddleware)

# 3. Analytics (track usage and performance)
app.add_middleware(AnalyticsMiddleware)

# 4. Audit logging (sees all requests with request_id)
app.add_middleware(AuditLoggingMiddleware)

# 5. Security headers (applied to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 6. Input sanitization (detect malicious input)
app.add_middleware(InputSanitizationMiddleware, enable_detection=True)

# 7. Request size limits
app.add_middleware(RequestSizeLimitMiddleware, max_size=SecurityConfig.MAX_REQUEST_SIZE)

# 8. CORS (must be after security middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)

# 9. Response compression (must be last, compresses all responses)
if os.getenv("COMPRESSION_ENABLED", "true").lower() == "true":
    app.add_middleware(CompressionMiddleware, minimum_size=500)

# =============================================================================
# API Versioning
# =============================================================================

# Include v1 API endpoints
app.include_router(api_v1.router)

# Include OAuth2/JWT endpoints (if available)
try:
    from .security import get_oauth2_router
    oauth2_router = get_oauth2_router()
    if oauth2_router is not None:
        app.include_router(oauth2_router)
except (ImportError, RuntimeError):
    # OAuth2 requires additional dependencies (python-multipart, pyjwt)
    pass

# =============================================================================
# WebSocket Endpoint
# =============================================================================

from fastapi import WebSocket

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time LLM streaming.

    Connects to the server and receive streaming LLM responses.

    Message Format:
    {
        "type": "connect",
        "api_key": "your-api-key",
        "session_id": "optional-session-id",
        "user_id": "optional-user-id"
    }

    After connecting, send chat messages:
    {
        "type": "chat",
        "message_id": "unique-id",
        "prompt": "Your question here",
        "persona": "oi-trader",  // optional
        "model": "llama3.1:8b",   // optional
        "temperature": 0.7,      // optional
        "max_tokens": 2000       // optional
    }

    The server will respond with:
    - stream_start: Stream is starting
    - stream_chunk: Text chunk (streamed)
    - stream_end: Stream complete
    - error: If something goes wrong

    Example:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/stream');

    ws.onopen = () => {
        ws.send(JSON.stringify({
            type: 'connect',
            api_key: 'dev-key-12345',
            session_id: 'my-session'
        }));
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        switch(msg.type) {
            case 'connected':
                console.log('Connected:', msg.connection_id);
                // Send chat
                ws.send(JSON.stringify({
                    type: 'chat',
                    message_id: 'msg-1',
                    prompt: 'What is the weather today?'
                }));
                break;
            case 'stream_chunk':
                console.log('Chunk:', msg.chunk.delta);
                break;
            case 'stream_end':
                console.log('Complete! Tokens:', msg.tokens_used);
                break;
            case 'error':
                console.error('Error:', msg.error.message);
                break;
        }
    };
    ```
    """
    from backend.websocket.handler import websocket_handler

    await websocket_handler(websocket)


# Legacy unversioned endpoints (for backward compatibility)
# These will be deprecated in favor of /v1/* endpoints


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, _auth: str = Depends(verify_api_key)) -> ChatResponse:
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

    Requires authentication via X-API-Key header.

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
        logger.info(f"Response to client: session_id={session_id}, context_used={context_used}, answer_preview={answer_preview}")
        logger.info(f"Full response JSON: {response.model_dump_json()}")

        return response

    except LlmProviderError as e:
        # Return user-friendly error message from the exception
        response = ChatResponse(
            answer=e.user_message,
            events=[],
            session_id=req.session_id or "",
            context_used=False
        )
        logger.error(f"LlmProviderError: {response.model_dump_json()}")
        return response

    except ValidationError as e:
        # Pydantic validation error - return error as JSON
        response = ChatResponse(
            answer="Validation error: Please try again.",
            events=[],
            session_id=req.session_id or "",
            context_used=False
        )
        logger.error(f"ValidationError: {response.model_dump_json()}")
        return response

    except Exception as e:
        # Catch-all for unexpected errors - return as JSON instead of crashing
        response = ChatResponse(
            answer=f"An error occurred: {str(e)}",
            events=[],
            session_id=req.session_id or "",
            context_used=False
        )
        logger.error(f"Exception: {response.model_dump_json()}")
        return response


@app.get("/health")
async def health():
    """
    Enhanced health check endpoint.

    Returns overall system status and individual component health.
    Checks: LLM provider, cache, database
    """
    from . import cache as cache_module
    from .orchestrator import llm as llm_module

    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "api_version": "v1",
        "components": {}
    }

    # Check LLM provider
    try:
        llm_info = llm_module.get_provider_info()
        health_status["components"]["llm"] = {
            "status": "ok",
            "provider": llm_info["provider"],
            "model": llm_info["model"]
        }
    except Exception as e:
        health_status["components"]["llm"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Check cache
    try:
        cache_stats = await cache_module.get_cache_stats()
        health_status["components"]["cache"] = {
            "status": "ok",
            **cache_stats
        }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Check database
    try:
        db_stats = db_management.get_db_size()
        health_status["components"]["database"] = {
            "status": "ok",
            "size_mb": db_stats.get("size_mb"),
            "usage_percent": db_stats.get("usage_percent")
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/health/live")
def health_live():
    """
    Liveness probe - simple check if service is running.

    Used by Kubernetes/container orchestration.
    """
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """
    Readiness probe - check if service is ready to handle requests.

    Used by Kubernetes/container orchestration.
    Checks if critical dependencies (LLM provider) are accessible.
    """
    from .orchestrator import llm as llm_module

    try:
        # Check if LLM provider is configured
        llm_info = llm_module.get_provider_info()
        return {
            "status": "ready",
            "llm_provider": llm_info["provider"]
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e)
        }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes application metrics in Prometheus format.
    Includes HTTP request metrics, LLM metrics, cache metrics, and database metrics.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response

    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


@app.get("/llm/info")
def llm_info():
    """Get current LLM provider configuration."""
    return get_provider_info()


@app.get("/personas")
def list_personas(_auth: str = Depends(verify_api_key)):
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
def create_new_session(user_id: str = None, _auth: str = Depends(verify_api_key)):
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
def get_session_info(session_id: str, _auth: str = Depends(verify_api_key)):
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
def get_session_history(session_id: str, limit: int = 10, _auth: str = Depends(verify_api_key)):
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
    limit: int = 5,
    _auth: str = Depends(verify_api_key)
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
    confidence: float = 1.0,
    _auth: str = Depends(verify_api_key)
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
def get_user_facts(user_id: str = None, fact_type: str = None, _auth: str = Depends(verify_api_key)):
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
def cleanup_old_sessions_endpoint(days: int = 30, _auth: str = Depends(verify_api_key)):
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
# Database Management Endpoints (Admin Only)
# =============================================================================

@app.get("/db/size")
def get_database_size(_admin: str = Depends(require_admin)):
    """
    Get current database size and usage percentage.

    Returns:
        Database size in MB, max size, and usage percentage
    """
    return db_management.get_db_size()


@app.get("/db/stats")
def get_database_stats(_admin: str = Depends(require_admin)):
    """
    Get detailed database statistics.

    Returns:
        Comprehensive database statistics including row counts and size info
    """
    return db_management.get_db_stats()


@app.get("/db/status")
def check_database_status(_admin: str = Depends(require_admin)):
    """
    Check if database is approaching or exceeding size limits.

    Returns:
        Status (ok/warning/critical) and recommended actions
    """
    return db_management.check_size_limits()


@app.post("/db/cleanup/auto")
def auto_cleanup(_admin: str = Depends(require_admin)):
    """
    Automatically cleanup old data if approaching size limits.

    Performs aggressive cleanup if critical, normal cleanup if warning.

    Returns:
        Cleanup results including deleted counts and new size
    """
    return db_management.auto_cleanup_if_needed()


@app.post("/db/archive")
def archive_conversations(days: int = 90, compress: bool = True, _admin: str = Depends(require_admin)):
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
def vacuum_database(_admin: str = Depends(require_admin)):
    """
    Reclaim unused space in database.

    Runs VACUUM to compact the database file.

    Returns:
        Size before and after vacuum operation
    """
    return db_management.vacuum_database()


@app.post("/db/optimize")
def optimize_database(_admin: str = Depends(require_admin)):
    """
    Optimize database for better performance.

    Runs VACUUM, ANALYZE, and REINDEX operations.

    Returns:
        Optimization results and statistics
    """
    return db_management.optimize_database()


@app.get("/db/recommendations")
def get_storage_recommendations(_admin: str = Depends(require_admin)):
    """
    Get storage management recommendations.

    Analyzes current database state and provides actionable recommendations.

    Returns:
        List of recommendations based on current usage
    """
    return db_management.get_storage_recommendations()


# =============================================================================
# Background Task Endpoints
# =============================================================================

from typing import List, Optional
from pydantic import BaseModel


class TaskSubmitRequest(BaseModel):
    """Request model for submitting a background task."""
    prompt: str
    persona: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    use_cache: bool = True


class BatchTaskRequest(BaseModel):
    """Request model for submitting batch tasks."""
    requests: List[dict]
    persona: Optional[str] = None
    use_cache: bool = True


@app.post("/tasks/llm")
def submit_llm_task(req: TaskSubmitRequest, auth: str = Depends(verify_api_key)):
    """
    Submit an LLM request for background processing.

    The task will be processed asynchronously by Celery workers.
    Returns a task_id that can be used to check status and retrieve results.

    Args:
        req: Task request with prompt and optional parameters
        auth: API key authentication (required)

    Returns:
        Task ID for tracking
    """
    from backend.tasks.llm_tasks import process_llm_request_task

    result = process_llm_request_task.delay(
        prompt=req.prompt,
        persona=req.persona,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        use_cache=req.use_cache,
    )

    return {
        "task_id": result.id,
        "status": "submitted",
        "message": "Task submitted for background processing",
    }


@app.post("/tasks/batch")
def submit_batch_task(req: BatchTaskRequest, auth: str = Depends(verify_api_key)):
    """
    Submit multiple LLM requests for batch processing.

    All requests will be processed in parallel by Celery workers.

    Args:
        req: Batch request with list of prompts
        auth: API key authentication (required)

    Returns:
        Batch task ID for tracking
    """
    from backend.tasks.llm_tasks import process_batch_llm_task

    result = process_batch_llm_task.delay(
        requests=req.requests,
        persona=req.persona,
        use_cache=req.use_cache,
    )

    return {
        "task_id": result.id,
        "status": "submitted",
        "request_count": len(req.requests),
        "message": "Batch task submitted for background processing",
    }


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str, auth: str = Depends(verify_api_key)):
    """
    Get the status and result of a background task.

    Args:
        task_id: Task identifier from submission
        auth: API key authentication (required)

    Returns:
        Task status and result (if completed)
    """
    from backend.tasks.celery_app import get_celery_app

    celery_app = get_celery_app()
    try:
        from celery.result import AsyncResult
    except ImportError:
        # Celery not installed, return error
        return {
            "task_id": task_id,
            "status": "error",
            "error": "Celery not installed. Install with: pip install celery[redis]",
        }

    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = str(result.info)
    else:
        response["info"] = str(result.info)

    return response


@app.delete("/tasks/{task_id}")
def cancel_task(task_id: str, auth: str = Depends(verify_api_key)):
    """
    Cancel a running background task.

    Args:
        task_id: Task identifier to cancel
        auth: API key authentication (required)

    Returns:
        Cancellation status
    """
    from backend.tasks.celery_app import get_celery_app

    celery_app = get_celery_app()
    try:
        from celery.result import AsyncResult
    except ImportError:
        return {
            "task_id": task_id,
            "status": "error",
            "error": "Celery not installed. Install with: pip install celery[redis]",
        }

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return {
            "task_id": task_id,
            "status": "already_completed",
            "message": "Task has already completed",
        }

    result.revoke(terminate=True, signal="SIGTERM")

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "Task cancellation requested",
    }


@app.post("/tasks/cache/clear")
def clear_llm_cache(pattern: Optional[str] = None, auth: str = Depends(verify_api_key)):
    """
    Clear the LLM response cache.

    Args:
        pattern: Optional cache key pattern to clear (clears all if not specified)
        auth: API key authentication (required)

    Returns:
        Cache clear results
    """
    from backend.tasks.llm_tasks import clear_llm_cache_task

    result = clear_llm_cache_task.delay(pattern=pattern)

    return {
        "task_id": result.id,
        "status": "submitted",
        "message": "Cache clear task submitted",
    }


# =============================================================================
# Analytics Endpoints
# =============================================================================

@app.get("/analytics/report")
def get_analytics_report(hours: int = 1, auth: str = Depends(verify_api_key)):
    """
    Generate an analytics report for the specified time period.

    Args:
        hours: Number of hours to analyze (default: 1, max: 168)
        auth: API key authentication (required)

    Returns:
        Analytics data including request counts, response times, etc.
    """
    from backend.analytics import get_analytics_summary

    if hours > 168:
        hours = 168

    result = get_analytics_summary(hours=hours)
    return result


@app.get("/analytics/usage")
def get_usage(hours: int = 1, auth: str = Depends(verify_api_key)):
    """
    Get usage statistics for the specified time period.

    Args:
        hours: Number of hours to analyze (default: 1, max: 168)
        auth: API key authentication (required)

    Returns:
        Usage statistics including request counts, token usage, etc.
    """
    from backend.analytics import get_usage_stats

    if hours > 168:
        hours = 168

    result = get_usage_stats(hours=hours)
    return result


@app.get("/analytics/performance")
def get_performance(hours: int = 1, auth: str = Depends(verify_api_key)):
    """
    Get performance metrics for the specified time period.

    Args:
        hours: Number of hours to analyze (default: 1, max: 168)
        auth: API key authentication (required)

    Returns:
        Performance metrics including response times, percentiles, etc.
    """
    from backend.analytics import get_performance_metrics

    if hours > 168:
        hours = 168

    result = get_performance_metrics(hours=hours)
    return result


@app.post("/analytics/health-check")
def trigger_health_check(auth: str = Depends(verify_api_key)):
    """
    Trigger a comprehensive system health check.

    Args:
        auth: API key authentication (required)

    Returns:
        Detailed health status of all system components
    """
    from backend.tasks.monitoring_tasks import check_system_health_task

    result = check_system_health_task()
    return result


# =============================================================================
# Alert Management Endpoints
# =============================================================================

@app.get("/alerts/active")
def get_active_alerts(
    severity: Optional[str] = None,
    auth: str = Depends(verify_api_key)
):
    """
    Get all active alerts.

    Args:
        severity: Optional filter by severity (info, warning, error, critical)
        auth: API key authentication (required)

    Returns:
        List of active alerts
    """
    from backend.monitoring import get_alert_manager, AlertSeverity

    alert_manager = get_alert_manager()

    severity_filter = None
    if severity:
        try:
            severity_filter = AlertSeverity(severity)
        except ValueError:
            return {"error": f"Invalid severity: {severity}"}

    alerts = alert_manager.get_active_alerts(severity=severity_filter)

    return {
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "severity": a.severity.value,
                "status": a.status.value,
                "timestamp": a.timestamp,
                "metric": {
                    "name": a.metric_name,
                    "value": a.metric_value,
                    "threshold": a.threshold,
                },
            }
            for a in alerts
        ],
    }


@app.get("/alerts/history")
def get_alert_history(hours: int = 24, limit: int = 100, auth: str = Depends(verify_api_key)):
    """
    Get alert history.

    Args:
        hours: Number of hours to look back (default: 24, max: 168)
        limit: Maximum number of alerts to return (default: 100, max: 1000)
        auth: API key authentication (required)

    Returns:
        List of historical alerts
    """
    from backend.monitoring import get_alert_manager

    if hours > 168:
        hours = 168
    if limit > 1000:
        limit = 1000

    alert_manager = get_alert_manager()
    alerts = alert_manager.get_alert_history(hours=hours, limit=limit)

    return {
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "severity": a.severity.value,
                "status": a.status.value,
                "timestamp": a.timestamp,
                "metric": {
                    "name": a.metric_name,
                    "value": a.metric_value,
                    "threshold": a.threshold,
                },
                "acknowledged_by": a.acknowledged_by,
                "acknowledged_at": a.acknowledged_at,
                "resolved_at": a.resolved_at,
            }
            for a in alerts
        ],
    }


@app.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, acknowledged_by: str, auth: str = Depends(verify_api_key)):
    """
    Acknowledge an active alert.

    Args:
        alert_id: Alert identifier
        acknowledged_by: Name of user acknowledging the alert
        auth: API key authentication (required)

    Returns:
        Acknowledgment status
    """
    from backend.monitoring import get_alert_manager

    alert_manager = get_alert_manager()
    success = alert_manager.acknowledge_alert(alert_id, acknowledged_by)

    if not success:
        return {
            "success": False,
            "message": f"Alert {alert_id} not found or already resolved",
        }

    return {
        "success": True,
        "message": f"Alert {alert_id} acknowledged by {acknowledged_by}",
    }


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, auth: str = Depends(verify_api_key)):
    """
    Resolve an active or acknowledged alert.

    Args:
        alert_id: Alert identifier
        auth: API key authentication (required)

    Returns:
        Resolution status
    """
    from backend.monitoring import get_alert_manager

    alert_manager = get_alert_manager()
    success = alert_manager.resolve_alert(alert_id)

    if not success:
        return {
            "success": False,
            "message": f"Alert {alert_id} not found",
        }

    return {
        "success": True,
        "message": f"Alert {alert_id} resolved",
    }


@app.get("/alerts/summary")
def get_alerts_summary(auth: str = Depends(verify_api_key)):
    """
    Get a summary of alert status.

    Args:
        auth: API key authentication (required)

    Returns:
        Alert summary statistics
    """
    from backend.monitoring import get_alert_manager

    alert_manager = get_alert_manager()
    summary = alert_manager.get_alert_summary()

    return summary


@app.get("/alerts/rules")
def list_alert_rules(auth: str = Depends(verify_api_key)):
    """
    List all alert rules.

    Args:
        auth: API key authentication (required)

    Returns:
        List of alert rules
    """
    from backend.monitoring import get_alert_manager

    alert_manager = get_alert_manager()

    return {
        "count": len(alert_manager.rules),
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "metric_name": r.metric_name,
                "condition": r.condition,
                "threshold": r.threshold,
                "severity": r.severity.value,
                "enabled": r.enabled,
                "cooldown_seconds": r.cooldown_seconds,
            }
            for r in alert_manager.rules.values()
        ],
    }


# =============================================================================
# API Gateway Endpoints
# =============================================================================

from typing import Dict, Any
from pydantic import BaseModel


class TransformationRequest(BaseModel):
    """Request for transformation testing."""
    data: Dict[str, Any]
    headers: Dict[str, str] = {}


class AggregationRequest(BaseModel):
    """Request for API aggregation."""
    calls: List[Dict[str, Any]]  # List of API call configurations
    merge_strategy: str = "merge"  # append, merge, first, all


@app.post("/gateway/transform")
async def test_transform(
    req: TransformationRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Test request/response transformation.

    Args:
        req: Transformation request with data and headers
        auth: API key authentication (required)

    Returns:
        Transformed data and headers
    """
    from backend.gateway import transform_request, transform_response

    transformed_data, transformed_headers = await transform_request(req.data, req.headers)

    # Also demonstrate response transformation
    transformed_response = await transform_response(transformed_data)

    return {
        "original_data": req.data,
        "original_headers": req.headers,
        "transformed_data": transformed_data,
        "transformed_headers": transformed_headers,
        "transformed_response": transformed_response,
    }


@app.post("/gateway/aggregate")
async def aggregate_apis(
    req: AggregationRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Aggregate responses from multiple APIs.

    Args:
        req: Aggregation request with API calls
        auth: API key authentication (required)

    Returns:
        Aggregated responses from all APIs
    """
    from backend.gateway import aggregate_responses, APICall, MergeStrategy

    # Convert API call configs to APICall objects
    api_calls = []
    for call_config in req.calls:
        api_calls.append(APICall(**call_config))

    # Convert merge strategy string to enum
    try:
        merge_strategy = MergeStrategy(req.merge_strategy)
    except ValueError:
        return {"error": f"Invalid merge_strategy: {req.merge_strategy}"}

    result = await aggregate_responses(api_calls, merge_strategy)

    return {
        "success": result.success,
        "partial": result.partial,
        "results": result.results,
        "errors": result.errors,
        "total_duration_ms": result.total_duration_ms,
    }


class RouteConfigRequest(BaseModel):
    """Request for adding a route."""
    name: str
    match_type: str  # path, prefix, regex, header, query
    pattern: str
    target_url: str
    headers: Dict[str, str] = {}
    strip_prefix: bool = False
    weight: int = 1
    timeout: float = 30.0
    methods: List[str] = ["GET", "POST", "PUT", "DELETE"]


@app.post("/gateway/routes")
async def add_route(
    req: RouteConfigRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Add a new route to the gateway.

    Args:
        req: Route configuration
        auth: API key authentication (required)

    Returns:
        Route addition status
    """
    from backend.gateway import get_router, RouteConfig, RouteMatchType

    # Convert match_type string to enum
    try:
        match_type = RouteMatchType(req.match_type)
    except ValueError:
        return {"error": f"Invalid match_type: {req.match_type}"}

    route_config = RouteConfig(
        name=req.name,
        match_type=match_type,
        pattern=req.pattern,
        target_url=req.target_url,
        headers=req.headers,
        strip_prefix=req.strip_prefix,
        weight=req.weight,
        timeout=req.timeout,
        methods=req.methods,
    )

    router = get_router()
    router.add_route(route_config)

    return {
        "success": True,
        "message": f"Route '{req.name}' added successfully",
    }


@app.delete("/gateway/routes/{route_name}")
async def remove_route(
    route_name: str,
    auth: str = Depends(verify_api_key)
):
    """
    Remove a route from the gateway.

    Args:
        route_name: Name of the route to remove
        auth: API key authentication (required)

    Returns:
        Route removal status
    """
    from backend.gateway import get_router

    router = get_router()
    removed = router.remove_route(route_name)

    if removed:
        return {
            "success": True,
            "message": f"Route '{route_name}' removed successfully",
        }
    else:
        return {
            "success": False,
            "message": f"Route '{route_name}' not found",
        }


@app.get("/gateway/routes")
async def list_routes(auth: str = Depends(verify_api_key)):
    """
    List all configured gateway routes.

    Args:
        auth: API key authentication (required)

    Returns:
        List of all routes
    """
    from backend.gateway import get_router

    router = get_router()

    return {
        "count": len(router.routes),
        "routes": [
            {
                "name": route.name,
                "match_type": route.match_type.value,
                "pattern": route.pattern,
                "target_url": route.target_url,
                "methods": route.methods,
                "weight": route.weight,
                "timeout": route.timeout,
            }
            for route in router.routes
        ],
    }


@app.post("/loadtest/run", tags=["Load Testing"])
async def run_load_test_endpoint(
    config: dict,
    _: None = Depends(verify_api_key),
) -> dict:
    """
    Run a load test against a target endpoint.

    Requires API key authentication.

    Args:
        config: Load test configuration
            - name: Test name
            - target_url: URL to test
            - method: HTTP method (GET, POST, etc.)
            - headers: Request headers
            - body: Request body (for POST/PUT)
            - params: Query parameters
            - concurrent_users: Number of concurrent users
            - requests_per_user: Requests per user
            - ramp_up_time: Delay between starting users
            - timeout: Request timeout

    Returns:
        Load test results with metrics
    """
    from backend.loadtest import run_load_test, LoadTestConfig

    test_config = LoadTestConfig(**config)
    result = await run_load_test(test_config)

    return {
        "test_name": result.test_name,
        "status": result.status.value,
        "duration_seconds": result.end_time - result.start_time,
        "total_requests": result.total_requests,
        "successful_requests": result.successful_requests,
        "failed_requests": result.failed_requests,
        "requests_per_second": result.requests_per_second,
        "response_time_ms": {
            "avg": result.avg_response_time_ms,
            "min": result.min_response_time_ms,
            "max": result.max_response_time_ms,
            "p50": result.p50_response_time_ms,
            "p95": result.p95_response_time_ms,
            "p99": result.p99_response_time_ms,
        },
        "errors": result.errors[:10],  # First 10 errors
    }


@app.post("/loadtest/scenario/simple", tags=["Load Testing"])
async def load_test_simple_get(
    url: str,
    concurrent_users: int = 10,
    requests_per_user: int = 10,
    _: None = Depends(verify_api_key),
) -> dict:
    """
    Run a simple GET load test against a URL.

    Requires API key authentication.

    Args:
        url: Target URL to test
        concurrent_users: Number of concurrent users
        requests_per_user: Requests per user

    Returns:
        Load test results
    """
    from backend.loadtest import run_load_test, LoadTestScenarios

    config = LoadTestScenarios.simple_get(
        url=url,
        concurrent_users=concurrent_users,
        requests_per_user=requests_per_user,
    )
    result = await run_load_test(config)

    return {
        "test_name": result.test_name,
        "status": result.status.value,
        "duration_seconds": result.end_time - result.start_time,
        "total_requests": result.total_requests,
        "successful_requests": result.successful_requests,
        "failed_requests": result.failed_requests,
        "requests_per_second": result.requests_per_second,
        "response_time_ms": {
            "avg": result.avg_response_time_ms,
            "min": result.min_response_time_ms,
            "max": result.max_response_time_ms,
            "p50": result.p50_response_time_ms,
            "p95": result.p95_response_time_ms,
            "p99": result.p99_response_time_ms,
        },
    }


@app.post("/loadtest/scenario/chat", tags=["Load Testing"])
async def load_test_chat_endpoint(
    base_url: str,
    concurrent_users: int = 5,
    requests_per_user: int = 5,
    _: None = Depends(verify_api_key),
) -> dict:
    """
    Run a load test against the chat compression endpoint.

    Requires API key authentication.

    Args:
        base_url: Base URL of the API (e.g., http://localhost:8000)
        concurrent_users: Number of concurrent users
        requests_per_user: Requests per user

    Returns:
        Load test results
    """
    from backend.loadtest import run_load_test, LoadTestScenarios

    config = LoadTestScenarios.chat_compression(
        base_url=base_url,
        concurrent_users=concurrent_users,
        requests_per_user=requests_per_user,
    )
    result = await run_load_test(config)

    return {
        "test_name": result.test_name,
        "status": result.status.value,
        "duration_seconds": result.end_time - result.start_time,
        "total_requests": result.total_requests,
        "successful_requests": result.successful_requests,
        "failed_requests": result.failed_requests,
        "requests_per_second": result.requests_per_second,
        "response_time_ms": {
            "avg": result.avg_response_time_ms,
            "min": result.min_response_time_ms,
            "max": result.max_response_time_ms,
            "p50": result.p50_response_time_ms,
            "p95": result.p95_response_time_ms,
            "p99": result.p99_response_time_ms,
        },
    }

