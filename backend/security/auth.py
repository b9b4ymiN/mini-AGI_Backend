"""
Security module for API authentication and authorization.

Provides API key authentication, rate limiting, and security middleware.
"""

import os
import secrets
import time
from typing import Optional
from functools import wraps
from collections import defaultdict
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logging_config import get_logger
logger = get_logger(__name__)

# Environment variables for API keys
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Default API keys (should be overridden by environment)
VALID_API_KEYS = set(
    os.getenv("API_KEYS", "dev-key-12345").split(",")
)
# Clean up whitespace and filter empty strings
VALID_API_KEYS = {key.strip() for key in VALID_API_KEYS if key.strip()}

# Master bypass key for admin operations
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-key-master-12345")


# Import Redis-based rate limiter
from backend.security.rate_limit import get_rate_limiter, RedisRateLimiter

# Use Redis rate limiter for distributed rate limiting
_rate_limiter: Optional[RedisRateLimiter] = None


def get_global_rate_limiter() -> RedisRateLimiter:
    """Get or initialize the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = get_rate_limiter()
    return _rate_limiter


# Legacy RateLimiter class kept for backwards compatibility
class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Tracks requests per API key within a time window.
    """

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # Structure: {api_key: [(timestamp, count), ...]}
        self.minute_window = defaultdict(list)
        self.hour_window = defaultdict(list)
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self):
        """Remove entries older than the time windows."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        # Clean minute window (keep only last 60 seconds)
        cutoff_minute = now - 60
        for key in list(self.minute_window.keys()):
            self.minute_window[key] = [
                (ts, count) for ts, count in self.minute_window[key]
                if ts > cutoff_minute
            ]
            if not self.minute_window[key]:
                del self.minute_window[key]

        # Clean hour window (keep only last 3600 seconds)
        cutoff_hour = now - 3600
        for key in list(self.hour_window.keys()):
            self.hour_window[key] = [
                (ts, count) for ts, count in self.hour_window[key]
                if ts > cutoff_hour
            ]
            if not self.hour_window[key]:
                del self.hour_window[key]

        self._last_cleanup = now

    def check_rate_limit(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Check if the API key is within rate limits.

        Args:
            api_key: The API key to check

        Returns:
            Tuple of (allowed, error_message)
        """
        self._cleanup_old_entries()
        now = time.time()

        # Check minute limit
        recent_minute = [
            count for ts, count in self.minute_window[api_key]
            if ts > now - 60
        ]
        minute_count = sum(recent_minute)

        if minute_count >= self.requests_per_minute:
            retry_after = 60 - int(now - self.minute_window[api_key][0][0])
            return False, f"Rate limit exceeded. {retry_after}s until reset."

        # Check hour limit
        recent_hour = [
            count for ts, count in self.hour_window[api_key]
            if ts > now - 3600
        ]
        hour_count = sum(recent_hour)

        if hour_count >= self.requests_per_hour:
            retry_after = 3600 - int(now - self.hour_window[api_key][0][0])
            return False, f"Hourly rate limit exceeded. {retry_after}s until reset."

        # Record this request
        self.minute_window[api_key].append((now, 1))
        self.hour_window[api_key].append((now, 1))

        return True, None


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
)


async def verify_api_key(
    request: Request,
    api_key_header: Optional[str] = Security(API_KEY_HEADER)
) -> str:
    """
    Verify API key from request header.

    Args:
        request: FastAPI request object
        api_key_header: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check for admin bypass in query param (for testing)
    if api_key_header is None:
        api_key_header = request.query_params.get("api_key")

    if not api_key_header:
        logger.warning("request_without_api_key", client=request.client.host if request.client else "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check admin key (bypasses rate limiting)
    if secrets.compare_digest(api_key_header, ADMIN_API_KEY):
        logger.info("admin_api_key_used", client=request.client.host if request.client else "unknown")
        return api_key_header

    # Check regular API keys
    if not any(secrets.compare_digest(api_key_header, valid_key) for valid_key in VALID_API_KEYS):
        logger.warning("invalid_api_key_attempt", client=request.client.host if request.client else "unknown")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key."
        )

    # Check rate limits using Redis rate limiter
    rate_limiter = get_global_rate_limiter()
    is_limited, retry_after = await rate_limiter.is_rate_limited(api_key_header, window="minute")
    if is_limited:
        logger.warning("rate_limit_exceeded", client=request.client.host if request.client else "unknown", api_key=api_key_header[:8] + "...")
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please retry after {retry_after}s." if retry_after else "Rate limit exceeded.",
            headers=headers,
        )

    return api_key_header


# Endpoints that bypass authentication (health checks, docs, metrics)
BYPASS_ENDPOINTS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def should_bypass_auth(request: Request) -> bool:
    """
    Check if request should bypass authentication.

    Args:
        request: FastAPI request object

    Returns:
        True if authentication should be bypassed
    """
    return any(
        request.url.path.startswith(endpoint)
        for endpoint in BYPASS_ENDPOINTS
    )


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware that adds authentication and rate limiting.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for bypass endpoints
        if should_bypass_auth(request):
            return await call_next(request)

        # Verify API key
        try:
            await verify_api_key(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        response = await call_next(request)
        return response


from starlette.responses import JSONResponse


class SecurityConfig:
    """
    Security configuration settings.
    """

    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

    # Request size limits (in bytes)
    MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))  # 10MB default

    # API keys
    VALID_API_KEYS = VALID_API_KEYS
    ADMIN_API_KEY = ADMIN_API_KEY

    @classmethod
    def reload_from_env(cls):
        """Reload configuration from environment variables."""
        cls.VALID_API_KEYS = set(
            os.getenv("API_KEYS", "dev-key-12345").split(",")
        )
        cls.VALID_API_KEYS = {key.strip() for key in cls.VALID_API_KEYS if key.strip()}
        cls.ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-key-master-12345")
        cls.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        cls.RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
        cls.MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))

        logger.info(f"Security config reloaded: {len(cls.VALID_API_KEYS)} API keys loaded")


def require_admin(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Dependency that requires admin API key.

    Use for sensitive operations like database cleanup, configuration changes.

    Raises:
        HTTPException: If not an admin key
    """
    if api_key is None or not secrets.compare_digest(api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return api_key


async def verify_api_key_ws(api_key: str) -> dict:
    """
    Verify API key for WebSocket connections.

    Unlike verify_api_key, this returns a dict with auth info instead of
    raising HTTPException (which doesn't work with WebSockets).

    Args:
        api_key: API key to verify

    Returns:
        Dict with authentication result:
        - authenticated: bool
        - api_key_hash: str (hash of API key for logging)
        - user_id: Optional[str]
        - session_id: Optional[str]
        - error: Optional[str] (if authentication failed)

    Raises:
        ValueError: If API key is invalid
    """
    import hashlib

    if not api_key:
        raise ValueError("API key is required")

    # Check admin key
    if secrets.compare_digest(api_key, ADMIN_API_KEY):
        return {
            "authenticated": True,
            "api_key_hash": hashlib.sha256(api_key.encode()).hexdigest()[:16],
            "user_id": "admin",
            "is_admin": True,
        }

    # Check regular API keys
    if not any(secrets.compare_digest(api_key, valid_key) for valid_key in VALID_API_KEYS):
        raise ValueError("Invalid API key")

    # Check rate limits
    rate_limiter = get_global_rate_limiter()
    is_limited, retry_after = await rate_limiter.is_rate_limited(api_key, window="minute")
    if is_limited:
        raise ValueError(f"Rate limit exceeded. Retry after {retry_after}s")

    return {
        "authenticated": True,
        "api_key_hash": hashlib.sha256(api_key.encode()).hexdigest()[:16],
        "user_id": None,
        "is_admin": False,
    }
