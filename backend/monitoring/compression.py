"""
Response compression middleware using gzip.

Reduces bandwidth usage by compressing responses with gzip.
"""

import gzip
import io
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

from backend.logging_config import get_logger

logger = get_logger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress responses using gzip.

    Features:
    - Configurable minimum size threshold
    - Skip compression for small responses
    - Skip compression for already compressed content
    - Respect Accept-Encoding header
    """

    def __init__(
        self,
        app,
        minimum_size: int = 500,  # Only compress responses larger than 500 bytes
        compresslevel: int = 6,  # Compression level (0-9, 6 is default)
    ):
        """
        Initialize compression middleware.

        Args:
            app: FastAPI application
            minimum_size: Minimum response size in bytes to compress
            compresslevel: Compression level (0-9, higher = more compression but slower)
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and compress response if applicable.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Compressed or uncompressed response
        """
        # Process request
        response: Response = await call_next(request)

        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response

        # Skip compression for certain content types
        content_type = response.headers.get("content-type", "")
        if self._should_skip_compression(content_type):
            return response

        # Skip if already compressed
        if response.headers.get("content-encoding", ""):
            return response

        # Get response body
        body = getattr(response, "body", None)
        if body is None:
            return response

        # Check minimum size
        if len(body) < self.minimum_size:
            return response

        # Compress the body
        compressed_body = self._compress_body(body)

        # Only use compressed version if it's actually smaller
        if len(compressed_body) >= len(body):
            return response

        # Update response with compressed body
        response.body = compressed_body
        response.headers["content-encoding"] = "gzip"
        response.headers["content-length"] = str(len(compressed_body))
        # Remove vary header if present, then add it back with accept-encoding
        if "vary" in response.headers:
            vary_values = [v.strip() for v in response.headers["vary"].split(",")]
            if "accept-encoding" not in [v.lower() for v in vary_values]:
                vary_values.append("Accept-Encoding")
            response.headers["vary"] = ", ".join(vary_values)
        else:
            response.headers["vary"] = "Accept-Encoding"

        return response

    def _should_skip_compression(self, content_type: str) -> bool:
        """
        Check if content type should be skipped from compression.

        Args:
            content_type: Response content type

        Returns:
            True if compression should be skipped
        """
        # Skip already compressed formats
        skip_types = [
            "application/gzip",
            "application/zip",
            "application/x-gzip",
            "application/x-compress",
            "application/x-zip-compressed",
            "image/",
            "video/",
            "audio/",
        ]

        content_type_lower = content_type.lower()
        for skip_type in skip_types:
            if content_type_lower.startswith(skip_type):
                return True

        return False

    def _compress_body(self, body: bytes) -> bytes:
        """
        Compress response body using gzip.

        Args:
            body: Response body bytes

        Returns:
            Compressed body bytes
        """
        buffer = io.BytesIO()
        with gzip.GzipFile(
            fileobj=buffer,
            mode="wb",
            compresslevel=self.compresslevel
        ) as gzip_file:
            gzip_file.write(body)
        return buffer.getvalue()
