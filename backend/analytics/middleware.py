"""
Analytics middleware for automatic request tracking.

This middleware integrates with the FastAPI request lifecycle to
automatically track all API requests for analytics purposes.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logging_config import get_logger
from backend.analytics import track_request

logger = get_logger(__name__)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track all API requests for analytics.

    Tracks:
    - Request count and rate
    - Response times
    - Status codes
    - Endpoints
    - HTTP methods
    - Error rates

    Usage:
        app.add_middleware(AnalyticsMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and track analytics.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response from downstream handler
        """
        start_time = time.time()

        # Get request info
        endpoint = request.url.path
        method = request.method

        # Get user info if available
        user_id = getattr(request.state, "user_id", None)
        api_key_hash = getattr(request.state, "api_key_hash", None)

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            # Re-raise after tracking
            raise
        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Track the request
            try:
                await track_request(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    user_id=user_id,
                    api_key=api_key_hash,
                    error=error,
                )
            except Exception as tracking_error:
                # Don't let analytics errors affect the request
                logger.warning("analytics_tracking_failed", error=str(tracking_error))

        return response
