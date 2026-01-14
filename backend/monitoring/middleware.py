"""
Monitoring middleware for automatic metrics collection.

Provides:
- Request duration tracking
- Request counting
- Error rate monitoring
- Route-based metrics
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logging_config import get_logger
from backend.monitoring import get_tracer
from opentelemetry import trace

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics.

    Tracks:
    - Request duration
    - Request count
    - Response status codes
    - HTTP methods
    - Route patterns
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with metrics collected
        """
        # Start timer
        start_time = time.time()

        # Get tracer for span creation
        tracer = get_tracer()

        # Create span for this request
        path_template = getattr(request.state, "route", None) or request.url.path
        span_name = f"{request.method} {path_template}"

        with tracer.start_as_current_span(span_name) as span:
            # Set span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("http.host", request.url.hostname)

            # Get client info
            if request.client:
                span.set_attribute("net.peer.ip", request.client.host)
                span.set_attribute("net.peer.port", request.client.host)

            # Process request
            try:
                response: Response = await call_next(request)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Set response attributes
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response.duration_ms", duration_ms)

                # Log slow requests
                if duration_ms > 1000:  # More than 1 second
                    logger.warning(
                        "slow_request",
                        method=request.method,
                        path=path_template,
                        duration_ms=f"{duration_ms:.2f}",
                        status=response.status_code
                    )

                return response

            except Exception as e:
                # Calculate duration for failed requests
                duration_ms = (time.time() - start_time) * 1000

                # Record error
                span.record_exception(e)
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))

                logger.error(
                    "request_failed",
                    method=request.method,
                    path=path_template,
                    error=str(e),
                    duration_ms=f"{duration_ms:.2f}"
                )

                raise
