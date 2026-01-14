"""
Structured logging configuration with structlog.

Provides JSON-formatted structured logging for production environments.
Supports both JSON output (production) and pretty console output (development).
"""

import sys
import logging
import os
from typing import Any
from pathlib import Path

import structlog
from structlog.types import EventDict, Processor


# =============================================================================
# Configuration
# =============================================================================

def should_use_json() -> bool:
    """
    Determine if JSON logging should be used.

    Returns:
        True if in production environment
    """
    return os.getenv("LOG_FORMAT", "pretty").lower() == "json"


def get_log_level() -> str:
    """
    Get log level from environment.

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    return os.getenv("LOG_LEVEL", "INFO").upper()


# =============================================================================
# Custom Processors
# =============================================================================

def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add request_id if present in context.

    This is useful for tracing requests through the system.
    """
    # Request ID can be added via structlog.contextvars.bind_contextvars(request_id=...)
    return event_dict


def add_app_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application name and version to log entries."""
    event_dict["app"] = "mini-agi-backend"
    event_dict["version"] = "1.0.0"
    return event_dict


def rename_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Rename 'level' to 'severity' for better compatibility with log aggregators.
    """
    if "level" in event_dict:
        event_dict["severity"] = event_dict.pop("level")
    return event_dict


def format_exc_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Format exception info with full traceback.

    This replaces the default structlog exception formatting.
    """
    if "exc_info" in event_dict:
        # Let structlog handle the exception formatting
        pass
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Drop the color_message key if present (used for pretty console output).
    """
    event_dict.pop("color_message", None)
    return event_dict


# =============================================================================
# Processor Chains
# =============================================================================

def get_shared_processors() -> list[Processor]:
    """
    Get processors shared by all logging configurations.

    Returns:
        List of structlog processors
    """
    return [
        # Add context from contextvars
        structlog.contextvars.merge_contextvars,

        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add log level
        structlog.stdlib.add_log_level,

        # Add application info
        add_app_info,

        # Add request ID if present
        add_request_id,

        # Handle exceptions
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def get_json_processors() -> list[Processor]:
    """
    Get processors for JSON logging (production).

    Returns:
        List of structlog processors
    """
    return get_shared_processors() + [
        # Rename level to severity
        rename_level,

        # Render final output as JSON
        structlog.processors.JSONRenderer(),
    ]


def get_console_processors() -> list[Processor]:
    """
    Get processors for console logging (development).

    Returns:
        List of structlog processors
    """
    return get_shared_processors() + [
        # Remove color_message key
        drop_color_message_key,

        # Pretty console output with colors
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback
        ),
    ]


# =============================================================================
# Configuration Function
# =============================================================================

def configure_logging(
    level: str | None = None,
    json_format: bool | None = None
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Force JSON format (True) or console format (False)
                    If None, determined from LOG_FORMAT env var
    """
    # Determine configuration
    if level is None:
        level = get_log_level()

    if json_format is None:
        json_format = should_use_json()

    # Choose processors based on format
    if json_format:
        processors = get_json_processors()
    else:
        processors = get_console_processors()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )

    # Configure uvicorn logging
    logging.getLogger("uvicorn").setLevel(getattr(logging, level))
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Log configuration
    log = structlog.get_logger()
    log.info(
        "Logging configured",
        log_level=level,
        format="json" if json_format else "console"
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Optional logger name (module path recommended)

    Returns:
        Structlog bound logger

    Example:
        from backend.logging_config import get_logger

        log = get_logger(__name__)
        log.info("User logged in", user_id="123", ip="192.168.1.1")
    """
    return structlog.get_logger(name)


# =============================================================================
# Request ID Middleware
# =============================================================================

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.

    The request ID is added to both the request state and logging context,
    making it easy to trace requests through the system.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add request ID."""
        # Generate or retrieve request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to request state for access in endpoints
        request.state.request_id = request_id

        # Add to logging context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Add response header
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Clear context for next request
        structlog.contextvars.unbind_contextvars("request_id")

        return response


# =============================================================================
# Module Convenience
# =============================================================================

# Export commonly used items
__all__ = [
    "configure_logging",
    "get_logger",
    "RequestIDMiddleware",
    "structlog",
]


# Auto-configure on import if not already configured
if not structlog.is_configured():
    configure_logging()
