"""
Standardized error handling for the API.

Provides:
- Consistent error response format
- HTTP exception handlers
- Validation error handling
- Error logging
- Error tracking
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.logging_config import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """
    Base exception for API errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        code: str = "api_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error for invalid input data."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(APIError):
    """Authentication error for invalid credentials."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="authentication_error",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(APIError):
    """Authorization error for insufficient permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="authorization_error",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        super().__init__(
            message=message,
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if retry_after:
            details = details or {}
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error."""

    def __init__(
        self,
        service: str = "Service",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if not message:
            message = f"{service} temporarily unavailable"

        super().__init__(
            message=message,
            code="service_unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class LLMProviderError(APIError):
    """LLM provider error."""

    def __init__(
        self,
        message: str = "LLM provider error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="llm_provider_error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def create_error_response(
    status_code: int,
    message: str,
    code: str = "api_error",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error details
        request_id: Request ID for tracing

    Returns:
        JSONResponse with standardized error format
    """
    error_response: Dict[str, Any] = {
        "error": {
            "message": message,
            "code": code,
            "status_code": status_code,
        }
    }

    if details:
        error_response["error"]["details"] = details

    if request_id:
        error_response["request_id"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=error_response,
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle APIError exceptions.

    Args:
        request: Incoming request
        exc: APIError exception

    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)

    # Log error
    logger.error(
        "api_error",
        error_code=exc.code,
        status_code=exc.status_code,
        message=exc.message,
        request_id=request_id,
        path=request.url.path,
        details=exc.details,
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        details=exc.details if exc.details else None,
        request_id=request_id,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException.

    Args:
        request: Incoming request
        exc: HTTPException

    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)

    # Determine error code from status code
    error_codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }

    code = error_codes.get(exc.status_code, "http_error")

    # Log error
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        code=code,
        detail=exc.detail,
        request_id=request_id,
        path=request.url.path,
    )

    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        code=code,
        request_id=request_id,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: Incoming request
        exc: RequestValidationError

    Returns:
        Standardized error response with validation details
    """
    request_id = getattr(request.state, "request_id", None)

    # Extract validation errors
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })

    details = {"errors": errors}

    # Log validation error
    logger.warning(
        "validation_error",
        request_id=request_id,
        path=request.url.path,
        errors=errors,
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        code="validation_error",
        details=details,
        request_id=request_id,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unhandled exceptions.

    Args:
        request: Incoming request
        exc: Unhandled exception

    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)

    # Log unexpected error
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        request_id=request_id,
        path=request.url.path,
        exc_info=True,
    )

    # Don't expose internal errors in production
    is_debug = logger.level <= 10  # DEBUG level

    message = "An unexpected error occurred" if not is_debug else str(exc)

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        code="internal_error",
        request_id=request_id,
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance

    Usage:
        from backend.errors import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
