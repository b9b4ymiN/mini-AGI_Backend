"""
Security module for API protection.

Provides authentication, rate limiting, input validation, and security headers.
"""

from .auth import (
    verify_api_key,
    verify_api_key_ws,
    should_bypass_auth,
    SecurityMiddleware,
    SecurityConfig,
    require_admin,
    RateLimiter,
    API_KEY_HEADER,
    API_KEY_NAME,
    BYPASS_ENDPOINTS,
    get_global_rate_limiter,
)

from .rate_limit import (
    RedisRateLimiter,
    get_rate_limiter,
    RateLimitConfig,
)

from .middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
    AuditLoggingMiddleware,
)

# Try to import JWT/OAuth2 modules (may not be available in all environments)
try:
    from .jwt_auth import (
        create_access_token,
        create_refresh_token,
        create_tokens_for_user,
        verify_access_token,
        verify_refresh_token,
        authenticate_user,
        get_user,
        Token,
        TokenData,
        User,
    )
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    from .jwt_dependencies import (
        oauth2_scheme,
        get_current_user,
        get_current_user_optional,
        get_current_active_user,
        require_scope,
        require_admin as require_jwt_admin,
        require_write,
        require_read,
    )
    JWT_DEPS_AVAILABLE = True
except ImportError:
    JWT_DEPS_AVAILABLE = False

# OAuth2 router lazy-loaded to avoid ImportError when python-multipart is not installed
oauth2_router = None
OAUTH2_AVAILABLE = False

def get_oauth2_router():
    """Lazy-load the OAuth2 router."""
    global oauth2_router, OAUTH2_AVAILABLE
    if oauth2_router is None:
        try:
            from .oauth2 import oauth2_router as _router
            oauth2_router = _router
            OAUTH2_AVAILABLE = True
        except (ImportError, RuntimeError):
            OAUTH2_AVAILABLE = False
            oauth2_router = None
    return oauth2_router


__all__ = [
    # API Key Authentication
    "verify_api_key",
    "verify_api_key_ws",
    "should_bypass_auth",
    "SecurityMiddleware",
    "SecurityConfig",
    "require_admin",
    "RateLimiter",
    "API_KEY_HEADER",
    "API_KEY_NAME",
    "BYPASS_ENDPOINTS",
    "get_global_rate_limiter",
    # Rate Limiting
    "RedisRateLimiter",
    "get_rate_limiter",
    "RateLimitConfig",
    # Middleware
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "InputSanitizationMiddleware",
    "AuditLoggingMiddleware",
]

# Conditionally add JWT exports
if JWT_AVAILABLE:
    __all__.extend([
        "create_access_token",
        "create_refresh_token",
        "create_tokens_for_user",
        "verify_access_token",
        "verify_refresh_token",
        "authenticate_user",
        "get_user",
        "Token",
        "TokenData",
        "User",
    ])

if JWT_DEPS_AVAILABLE:
    __all__.extend([
        "oauth2_scheme",
        "get_current_user",
        "get_current_user_optional",
        "get_current_active_user",
        "require_scope",
        "require_jwt_admin",
        "require_write",
        "require_read",
    ])

if OAUTH2_AVAILABLE:
    __all__.append("oauth2_router")
