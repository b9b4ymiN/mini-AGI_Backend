"""
API documentation examples and helpers.

Provides:
- Request/response examples for all endpoints
- Example data models
- Usage guides
"""

from typing import Any, Dict, List

# =============================================================================
# Common Examples
# =============================================================================

EXAMPLE_API_KEY = "dev-key-123456789"
EXAMPLE_ADMIN_KEY = "admin-key-master-12345"

# =============================================================================
# Chat Endpoint Examples
# =============================================================================

EXAMPLE_CHAT_REQUEST = {
    "persona": "oi-trader",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What's the current market trend?"
                }
            ]
        }
    ],
    "session_id": "session_abc123",
    "user_id": "user_123",
}

EXAMPLE_CHAT_RESPONSE = {
    "answer": "Based on recent analysis, the market is showing...",
    "events": [],
    "session_id": "session_abc123",
    "context_used": True,
}

# =============================================================================
# Persona Examples
# =============================================================================

EXAMPLE_PERSONAS_RESPONSE = {
    "personas": [
        {
            "id": "oi-trader",
            "name": "OI Trader",
            "file": "oi_trader.md",
            "exists": True,
        },
        {
            "id": "analyst",
            "name": "Financial Analyst",
            "file": "analyst.md",
            "exists": True,
        },
    ]
}

# =============================================================================
# Session Examples
# =============================================================================

EXAMPLE_CREATE_SESSION_RESPONSE = {
    "session_id": "session_xyz789"
}

EXAMPLE_SESSION_INFO_RESPONSE = {
    "session_id": "session_abc123",
    "user_id": "user_123",
    "created_at": "2024-01-13T10:00:00Z",
    "message_count": 5,
    "last_activity": "2024-01-13T10:30:00Z",
}

EXAMPLE_SESSION_HISTORY_RESPONSE = {
    "session_id": "session_abc123",
    "history": [
        {
            "role": "user",
            "content": "Hello!",
            "timestamp": "2024-01-13T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "Hi! How can I help you?",
            "timestamp": "2024-01-13T10:00:05Z",
        },
    ],
    "count": 2,
}

# =============================================================================
# Analytics Examples
# =============================================================================

EXAMPLE_ANALYTICS_REPORT = {
    "generated_at": "2024-01-13T12:00:00Z",
    "period": {
        "hours": 1,
        "start": "2024-01-13T11:00:00Z",
        "end": "2024-01-13T12:00:00Z",
    },
    "usage": {
        "total_requests": 150,
        "successful_requests": 145,
        "failed_requests": 5,
        "avg_response_time_ms": 250.5,
        "total_tokens_used": 45000,
        "cache_hits": 80,
        "cache_misses": 70,
        "unique_users": 10,
        "top_personas": {
            "oi-trader": 45,
            "analyst": 30,
            "default": 75,
        },
        "top_models": {
            "llama3.1:8b": 120,
            "gpt-4": 30,
        },
        "errors_by_type": {
            "rate_limit_exceeded": 3,
            "llm_error": 2,
        },
    },
    "performance": {
        "requests": {
            "total": 150,
            "successful": 145,
            "failed": 5,
            "success_rate": 0.967,
            "per_minute": 2.5,
        },
        "performance": {
            "avg_response_time_ms": 250.5,
            "p50_ms": 200,
            "p95_ms": 450,
            "p99_ms": 800,
        },
        "tokens": {
            "total_used": 45000,
            "avg_per_request": 300,
        },
        "cache": {
            "hits": 80,
            "misses": 70,
            "hit_rate": 0.533,
        },
        "users": {
            "unique": 10,
        },
    },
}

# =============================================================================
# Task Examples
# =============================================================================

EXAMPLE_SUBMIT_TASK_REQUEST = {
    "prompt": "Analyze the following text...",
    "persona": "analyst",
    "model": "llama3.1:8b",
    "temperature": 0.7,
    "max_tokens": 2000,
    "use_cache": True,
}

EXAMPLE_SUBMIT_TASK_RESPONSE = {
    "task_id": "abc123-def456-ghi789",
    "status": "submitted",
    "message": "Task submitted for background processing",
}

EXAMPLE_TASK_STATUS_RESPONSE = {
    "task_id": "abc123-def456-ghi789",
    "status": "SUCCESS",
    "ready": True,
    "result": {
        "response": "Analysis complete...",
        "model": "llama3.1:8b",
        "tokens_used": 450,
        "cached": False,
    },
}

EXAMPLE_BATCH_TASK_REQUEST = {
    "requests": [
        {"prompt": "Analyze text 1"},
        {"prompt": "Analyze text 2"},
        {"prompt": "Analyze text 3"},
    ],
    "persona": "analyst",
    "use_cache": True,
}

# =============================================================================
# Alert Examples
# =============================================================================

EXAMPLE_ACTIVE_ALERTS_RESPONSE = {
    "count": 2,
    "alerts": [
        {
            "id": "high_error_rate_1",
            "title": "High Error Rate",
            "description": "Error rate exceeds 5%",
            "severity": "warning",
            "status": "active",
            "timestamp": 1705168800.0,
            "metric": {
                "name": "error_rate",
                "value": 0.08,
                "threshold": 0.05,
            },
        },
        {
            "id": "high_response_time_1",
            "title": "High Response Time",
            "description": "Average response time exceeds 5 seconds",
            "severity": "warning",
            "status": "active",
            "timestamp": 1705168860.0,
            "metric": {
                "name": "avg_response_time_ms",
                "value": 6500,
                "threshold": 5000,
            },
        },
    ],
}

EXAMPLE_ALERT_SUMMARY_RESPONSE = {
    "active_alerts": 2,
    "active_by_severity": {
        "info": 0,
        "warning": 2,
        "error": 0,
        "critical": 0,
    },
    "total_rules": 4,
    "enabled_rules": 4,
    "total_channels": 1,
    "enabled_channels": 1,
    "alerts_last_24h": 15,
}

# =============================================================================
# Health Check Examples
# =============================================================================

EXAMPLE_HEALTH_CHECK_RESPONSE = {
    "status": "ok",
    "version": "1.0.0",
    "api_version": "v1",
    "components": {
        "llm": {
            "status": "ok",
            "provider": "ollama",
            "model": "llama3.1:8b",
        },
        "cache": {
            "status": "ok",
            "type": "redis",
            "enabled": True,
        },
        "database": {
            "status": "ok",
            "size_mb": 5.99,
            "usage_percent": 0.12,
        },
    },
}

# =============================================================================
# Rate Limit Examples
# =============================================================================

EXAMPLE_RATE_LIMIT_RESPONSE = {
    "detail": "Rate limit exceeded. Please retry after 30s."
}

# =============================================================================
# Error Response Examples
# =============================================================================

EXAMPLE_ERROR_RESPONSE = {
    "error": {
        "message": "Validation failed",
        "code": "validation_error",
        "status_code": 422,
        "details": {
            "errors": [
                {
                    "field": "messages",
                    "message": "At least one message is required",
                    "type": "value_error",
                }
            ]
        }
    }
}

EXAMPLE_AUTH_ERROR_RESPONSE = {
    "error": {
        "message": "Invalid API key",
        "code": "authentication_error",
        "status_code": 401,
    }
}

# =============================================================================
# Documentation helper functions
# =============================================================================

def get_endpoint_examples(endpoint: str) -> Dict[str, Any]:
    """
    Get request/response examples for an endpoint.

    Args:
        endpoint: Endpoint path (e.g., "/chat", "/personas")

    Returns:
        Dictionary with request and response examples
    """
    examples_map = {
        "/chat": {
            "request": EXAMPLE_CHAT_REQUEST,
            "response": EXAMPLE_CHAT_RESPONSE,
        },
        "/personas": {
            "response": EXAMPLE_PERSONAS_RESPONSE,
        },
        "/sessions": {
            "response": EXAMPLE_CREATE_SESSION_RESPONSE,
        },
        "/analytics/report": {
            "response": EXAMPLE_ANALYTICS_REPORT,
        },
        "/tasks/llm": {
            "request": EXAMPLE_SUBMIT_TASK_REQUEST,
            "response": EXAMPLE_SUBMIT_TASK_RESPONSE,
        },
        "/alerts/active": {
            "response": EXAMPLE_ACTIVE_ALERTS_RESPONSE,
        },
        "/health": {
            "response": EXAMPLE_HEALTH_CHECK_RESPONSE,
        },
    }

    return examples_map.get(endpoint, {})


def get_example_headers(include_admin: bool = False) -> Dict[str, str]:
    """
    Get example request headers.

    Args:
        include_admin: Include admin API key

    Returns:
        Dictionary with example headers
    """
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": EXAMPLE_API_KEY,
    }

    if include_admin:
        headers["X-Admin-API-Key"] = EXAMPLE_ADMIN_KEY

    return headers


def get_usage_guide() -> str:
    """
    Get API usage guide.

    Returns:
        Markdown formatted usage guide
    """
    return """
# Mini-AGI Backend API Documentation

## Authentication

All endpoints require authentication via the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

Admin endpoints require the `X-Admin-API-Key` header:

```
X-Admin-API-Key: your-admin-key-here
```

## Core Endpoints

### Chat

Send a message to the LLM:

```
POST /chat
Content-Type: application/json
X-API-Key: your-api-key

{
  "persona": "oi-trader",
  "messages": [
    {
      "role": "user",
      "content": [{"type": "text", "text": "What's the market trend?"}]
    }
  ],
  "session_id": "session_abc123"
}
```

### List Personas

Get available personas:

```
GET /personas
X-API-Key: your-api-key
```

### Create Session

Create a new conversation session:

```
POST /sessions
X-API-Key: your-api-key
```

## Background Tasks

### Submit LLM Task

Submit an LLM request for background processing:

```
POST /tasks/llm
Content-Type: application/json
X-API-Key: your-api-key

{
  "prompt": "Analyze the following text...",
  "persona": "analyst",
  "model": "llama3.1:8b"
}
```

### Check Task Status

```
GET /tasks/{task_id}
X-API-Key: your-api-key
```

## Analytics

### Get Analytics Report

```
GET /analytics/report?hours=24
X-API-Key: your-api-key
```

### Get Usage Statistics

```
GET /analytics/usage?hours=1
X-API-Key: your-api-key
```

## Alerts

### Get Active Alerts

```
GET /alerts/active
X-API-Key: your-api-key
```

### Acknowledge Alert

```
POST /alerts/{alert_id}/acknowledge?acknowledged_by=admin
X-API-Key: your-api-key
```

## Rate Limiting

The API implements rate limiting:
- Free tier: 10 requests/minute
- Basic tier: 30 requests/minute
- Pro tier: 100 requests/minute
- Enterprise tier: 1000 requests/minute

When rate limited, you'll receive a 429 status code with a `Retry-After` header.

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "message": "Error description",
    "code": "error_code",
    "status_code": 400,
    "details": {}
  }
}
```
"""
