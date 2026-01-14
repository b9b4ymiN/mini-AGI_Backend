"""
OpenTelemetry distributed tracing and Prometheus metrics.

Provides:
- Distributed tracing with OTLP/Jaeger
- Prometheus metrics using prometheus_client
- Request/response tracking
- LLM provider performance tracking
"""

import os
import time
from typing import Optional, Callable, Any, ContextManager
from contextlib import contextmanager
from functools import wraps

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False

from prometheus_client import Counter, Histogram

from backend.logging_config import get_logger

logger = get_logger(__name__)

# Global telemetry state
_tracer: Optional[trace.Tracer] = None
_telemetry_initialized: bool = False

# =============================================================================
# Prometheus Metrics (using prometheus_client)
# =============================================================================

# HTTP metrics
_http_request_duration: Optional[Histogram] = None
_http_request_count: Optional[Counter] = None

# LLM metrics
_llm_request_duration: Optional[Histogram] = None
_llm_request_count: Optional[Counter] = None
_llm_token_count: Optional[Counter] = None

# Cache metrics
_cache_hit_count: Optional[Counter] = None
_cache_miss_count: Optional[Counter] = None

# Database metrics
_db_query_duration: Optional[Histogram] = None
_db_query_count: Optional[Counter] = None


def init_telemetry(
    service_name: str = "mini-agi-backend",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
    enable_prometheus: bool = True,
    prometheus_port: int = 8000,
) -> None:
    """
    Initialize OpenTelemetry tracing and Prometheus metrics.

    Args:
        service_name: Name of the service
        service_version: Service version
        otlp_endpoint: OTLP collector endpoint (e.g., "http://jaeger:4317")
        enable_console_export: Enable console span export for debugging
        enable_prometheus: Enable Prometheus metrics
        prometheus_port: Port for Prometheus metrics server

    Environment variables:
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint
        TELEMETRY_ENABLED: Enable/disable telemetry (default: true)
        PROMETHEUS_PORT: Override Prometheus port
    """
    global _tracer, _telemetry_initialized
    global _http_request_duration, _http_request_count
    global _llm_request_duration, _llm_request_count, _llm_token_count
    global _cache_hit_count, _cache_miss_count
    global _db_query_duration, _db_query_count

    # Check if telemetry is disabled
    if not os.getenv("TELEMETRY_ENABLED", "true").lower() == "true":
        logger.info("telemetry_disabled")
        _telemetry_initialized = False
        return

    if _telemetry_initialized:
        logger.warning("telemetry_already_initialized")
        return

    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "service.environment": os.getenv("ENVIRONMENT", "development"),
        })

        # Initialize Tracing
        trace_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(trace_provider)

        # Configure OTLP exporter
        otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

        if otlp_endpoint and OTLP_AVAILABLE:
            logger.info("otlp_exporter_configured", endpoint=otlp_endpoint)
            otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
            exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers=otlp_headers if otlp_headers else None
            )
            trace_provider.add_span_processor(BatchSpanProcessor(exporter))

        # Configure console exporter for debugging
        if enable_console_export or os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true":
            logger.info("console_exporter_enabled")
            trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Get tracer
        _tracer = trace.get_tracer(__name__)

        # Initialize Prometheus Metrics
        if enable_prometheus:
            prometheus_port = int(os.getenv("PROMETHEUS_PORT", str(prometheus_port)))
            logger.info("prometheus_configured", port=prometheus_port)

            # Common label names for all metrics
            label_names = ["method", "path", "status"]

            # Initialize HTTP metrics
            _http_request_duration = Histogram(
                "http_request_duration_ms",
                "HTTP request duration in milliseconds",
                label_names
            )
            _http_request_count = Counter(
                "http_request_count",
                "Total HTTP requests",
                label_names
            )

            # Initialize LLM metrics
            _llm_request_duration = Histogram(
                "llm_request_duration_ms",
                "LLM request duration in milliseconds",
                ["model", "success"]
            )
            _llm_request_count = Counter(
                "llm_request_count",
                "Total LLM requests",
                ["model", "success"]
            )
            _llm_token_count = Counter(
                "llm_token_count",
                "Total tokens processed",
                ["model", "token_type"]
            )

            # Initialize cache metrics
            _cache_hit_count = Counter(
                "cache_hit_count",
                "Total cache hits",
                ["key_pattern"]
            )
            _cache_miss_count = Counter(
                "cache_miss_count",
                "Total cache misses",
                ["key_pattern"]
            )

            # Initialize database metrics
            _db_query_duration = Histogram(
                "db_query_duration_ms",
                "Database query duration in milliseconds",
                ["operation", "table", "success"]
            )
            _db_query_count = Counter(
                "db_query_count",
                "Total database queries",
                ["operation", "table", "success"]
            )

        _telemetry_initialized = True
        logger.info(
            "telemetry_initialized",
            service=service_name,
            version=service_version,
            tracing=bool(otlp_endpoint or enable_console_export),
            metrics=enable_prometheus
        )

    except Exception as e:
        logger.error("telemetry_init_failed", error=str(e))
        # Don't fail the app if telemetry fails to initialize
        _telemetry_initialized = False


def shutdown_telemetry() -> None:
    """Shutdown OpenTelemetry exporters and flush pending data."""
    global _telemetry_initialized

    if not _telemetry_initialized:
        return

    try:
        # Flush spans
        trace_provider = trace.get_tracer_provider()
        if hasattr(trace_provider, "shutdown"):
            trace_provider.shutdown()

        logger.info("telemetry_shutdown_complete")
    except Exception as e:
        logger.error("telemetry_shutdown_failed", error=str(e))
    finally:
        _telemetry_initialized = False


def get_tracer() -> trace.Tracer:
    """
    Get the OpenTelemetry tracer.

    Returns:
        Tracer instance
    """
    if _tracer is None:
        return trace.get_tracer(__name__)
    return _tracer


@contextmanager
def with_tracing(
    operation_name: str,
    **attributes
) -> ContextManager:
    """
    Context manager for automatic span creation.

    Usage:
        with with_tracing("llm.call", model="llama3"):
            result = call_llm(...)

    Args:
        operation_name: Name of the operation
        **attributes: Additional span attributes

    Yields:
        Span context
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(operation_name) as span:
        # Set attributes
        for key, value in attributes.items():
            span.set_attribute(key, str(value))

        try:
            yield span
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def track_llm_request(
    model: str,
    persona: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    duration_ms: float = 0,
    success: bool = True
) -> None:
    """
    Track LLM request metrics.

    Args:
        model: Model name (e.g., "llama3")
        persona: Persona used (if any)
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration_ms: Request duration in milliseconds
        success: Whether the request succeeded
    """
    if not _telemetry_initialized:
        return

    success_str = "true" if success else "false"

    if _llm_request_duration:
        _llm_request_duration.labels(
            model=model,
            success=success_str
        ).observe(duration_ms)

    if _llm_request_count:
        _llm_request_count.labels(
            model=model,
            success=success_str
        ).inc()

    if _llm_token_count:
        _llm_token_count.labels(
            model=model,
            token_type="total"
        ).inc(prompt_tokens + completion_tokens)


def track_cache_hit(key_pattern: str, hit: bool) -> None:
    """
    Track cache hit/miss metrics.

    Args:
        key_pattern: Cache key pattern (e.g., "llm", "user")
        hit: Whether it was a cache hit
    """
    if not _telemetry_initialized:
        return

    if hit:
        if _cache_hit_count:
            _cache_hit_count.labels(key_pattern=key_pattern).inc()
    else:
        if _cache_miss_count:
            _cache_miss_count.labels(key_pattern=key_pattern).inc()


def track_database_query(
    operation: str,
    table: str,
    duration_ms: float,
    success: bool = True
) -> None:
    """
    Track database query metrics.

    Args:
        operation: Operation type (e.g., "select", "insert", "update")
        table: Table name
        duration_ms: Query duration in milliseconds
        success: Whether the query succeeded
    """
    if not _telemetry_initialized:
        return

    success_str = "true" if success else "false"

    if _db_query_duration:
        _db_query_duration.labels(
            operation=operation,
            table=table,
            success=success_str
        ).observe(duration_ms)

    if _db_query_count:
        _db_query_count.labels(
            operation=operation,
            table=table,
            success=success_str
        ).inc()


def traced(operation_name: str = None):
    """
    Decorator to trace a function.

    Usage:
        @traced("llm.call")
        def call_llm(...):
            ...

    Args:
        operation_name: Name for the span (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with with_tracing(name):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with with_tracing(name):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
