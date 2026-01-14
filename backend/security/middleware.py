"""
Security middleware for request validation and security headers.

Provides request size limiting, content validation, and security header injection.
"""

import os
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import re

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request size limits.

    Rejects requests that exceed the configured maximum size.
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        """
        Initialize the request size limit middleware.

        Args:
            app: FastAPI application
            max_size: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check request size before processing.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response or 413 error if request too large
        """
        # Check content-length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        f"Request too large: {size} bytes from {request.client.host} "
                        f"(max: {self.max_size})"
                    )
                    return Response(
                        content=f"Request entity too large. Maximum size is {self.max_size} bytes.",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                    )
            except ValueError:
                logger.warning(f"Invalid content-length header: {content_length}")

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject security headers into all responses.

    Adds OWASP recommended security headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        response: Response = await call_next(request)

        # Security headers - OWASP recommendations
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = self._get_permissions_policy()
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Adjust CSP for documentation endpoints to allow CDN resources
        is_docs_endpoint = request.url.path in ("/docs", "/redoc", "/docs/oauth2-redirect")
        response.headers["Content-Security-Policy"] = self._get_csp(for_docs=is_docs_endpoint)

        # Remove server information (use del instead of pop for MutableHeaders)
        if "Server" in response.headers:
            del response.headers["Server"]

        return response

    def _get_csp(self, for_docs: bool = False) -> str:
        """
        Get Content Security Policy header value.

        Args:
            for_docs: If True, allow CDN resources for Swagger UI/ReDoc

        Returns:
            CSP header value
        """
        if for_docs:
            # Relaxed CSP for documentation endpoints - allow CDN resources
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        else:
            # Strict CSP for API endpoints
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

    def _get_permissions_policy(self) -> str:
        """
        Get Permissions-Policy header value.

        Returns:
            Permissions-Policy header value
        """
        return (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect and block potentially malicious input.

    Checks for common attack patterns in request data.
    """

    # Patterns for common injection attacks
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;.*\bshutdown\b)",
        r"('.*--)",
        r"(\|.*\bwc\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e",
        r"~\/",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r";\s*(ls|cat|rm|mv|cp|nc|netcat|curl|wget)\b",
        r"\|\s*(ls|cat|rm|mv|cp|nc|netcat|curl|wget)\b",
        r"`.*`",
        r"\$\(.*\)",
    ]

    def __init__(self, app, enable_detection: bool = True):
        """
        Initialize the input sanitization middleware.

        Args:
            app: FastAPI application
            enable_detection: Whether to enable attack detection
        """
        super().__init__(app)
        self.enable_detection = enable_detection

        # Compile regex patterns for performance
        self.sql_pattern = re.compile(
            "|".join(self.SQL_INJECTION_PATTERNS),
            re.IGNORECASE | re.DOTALL
        )
        self.xss_pattern = re.compile(
            "|".join(self.XSS_PATTERNS),
            re.IGNORECASE | re.DOTALL
        )
        self.path_pattern = re.compile(
            "|".join(self.PATH_TRAVERSAL_PATTERNS),
            re.IGNORECASE
        )
        self.command_pattern = re.compile(
            "|".join(self.COMMAND_INJECTION_PATTERNS),
            re.IGNORECASE
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check request data for malicious patterns.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response or 400 error if malicious input detected
        """
        if not self.enable_detection:
            return await call_next(request)

        # Skip detection for safe endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Check query parameters
        for key, value in request.query_params.items():
            if self._check_for_attack(str(value)):
                logger.warning(
                    f"Malicious input detected in query param '{key}' "
                    f"from {request.client.host}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected."
                )

        # Check path parameters
        for segment in request.url.path.split("/"):
            if segment and self._check_for_attack(segment):
                logger.warning(
                    f"Malicious input detected in path "
                    f"from {request.client.host}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected."
                )

        # For POST/PUT requests, we'll validate the body in Pydantic models
        # This middleware catches the obvious URL-based attacks

        return await call_next(request)

    def _check_for_attack(self, value: str) -> bool:
        """
        Check if a string contains attack patterns.

        Args:
            value: String to check

        Returns:
            True if attack pattern detected
        """
        # Check for SQL injection
        if self.sql_pattern.search(value):
            return True

        # Check for XSS
        if self.xss_pattern.search(value):
            return True

        # Check for path traversal
        if self.path_pattern.search(value):
            return True

        # Check for command injection
        if self.command_pattern.search(value):
            return True

        return False


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests for audit purposes.

    Logs request details including user, endpoint, and response status.
    """

    def __init__(self, app):
        """Initialize the audit logging middleware."""
        super().__init__(app)
        self.logger = logging.getLogger("audit")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request details.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response
        """
        start_time = time.time()
        api_key = request.headers.get("X-API-Key", "anonymous")[:8] + "..."

        # Log incoming request
        self.logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host} (key: {api_key})"
        )

        response = await call_next(request)

        # Log response
        duration = (time.time() - start_time) * 1000
        self.logger.info(
            f"Response: {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.2f}ms)"
        )

        return response


import time
