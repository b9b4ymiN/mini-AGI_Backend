"""
API router for gateway request routing.

Provides:
- Request routing based on rules
- Load balancing
- Service discovery
- Proxy functionality
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from pydantic import BaseModel, HttpUrl

from backend.logging_config import get_logger

logger = get_logger(__name__)


class RouteMatchType(Enum):
    """Types of route matching."""
    PATH = "path"  # Exact path match
    PREFIX = "prefix"  # Path prefix match
    REGEX = "regex"  # Regex pattern match
    HEADER = "header"  # Header-based routing
    QUERY = "query"  # Query parameter routing


@dataclass
class RouteConfig:
    """Configuration for a single route."""
    name: str
    match_type: RouteMatchType
    pattern: str  # Path, prefix, regex, header name, or query param
    target_url: str  # Target URL or service name
    headers: Dict[str, str] = field(default_factory=dict)
    strip_prefix: bool = False  # For prefix matching
    weight: int = 1  # For load balancing
    timeout: float = 30.0
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])


@dataclass
class RouteMatch:
    """Result of route matching."""
    route: RouteConfig
    matched_pattern: Optional[str] = None
    extracted_params: Dict[str, str] = field(default_factory=dict)


class APIRouter:
    """
    Routes requests to appropriate backend services.

    Features:
    - Pattern-based routing
    - Header-based routing
    - Load balancing
    - Request proxying
    """

    def __init__(self):
        """Initialize API router."""
        self.routes: List[RouteConfig] = []
        self._client: Optional[Any] = None

    def add_route(self, route: RouteConfig) -> None:
        """
        Add a route configuration.

        Args:
            route: Route configuration
        """
        self.routes.append(route)
        logger.info("route_added", name=route.name, pattern=route.pattern)

    def remove_route(self, name: str) -> bool:
        """
        Remove a route by name.

        Args:
            name: Route name

        Returns:
            True if route was removed
        """
        for i, route in enumerate(self.routes):
            if route.name == name:
                self.routes.pop(i)
                logger.info("route_removed", name=name)
                return True
        return False

    def match_route(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[RouteMatch]:
        """
        Find matching route for a request.

        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            query_params: Query parameters

        Returns:
            RouteMatch if found, None otherwise
        """
        headers = headers or {}
        query_params = query_params or {}

        for route in self.routes:
            # Check method
            if method not in route.methods:
                continue

            # Check match type
            if route.match_type == RouteMatchType.PATH:
                if path == route.pattern:
                    return RouteMatch(route=route)

            elif route.match_type == RouteMatchType.PREFIX:
                if path.startswith(route.pattern):
                    matched_pattern = route.pattern
                    remaining_path = path[len(matched_pattern):]
                    return RouteMatch(
                        route=route,
                        matched_pattern=matched_pattern,
                        extracted_params={"remaining_path": remaining_path},
                    )

            elif route.match_type == RouteMatchType.REGEX:
                if re.match(route.pattern, path):
                    return RouteMatch(route=route)

            elif route.match_type == RouteMatchType.HEADER:
                header_value = headers.get(route.pattern)
                if header_value:
                    return RouteMatch(
                        route=route,
                        matched_pattern=header_value,
                    )

            elif route.match_type == RouteMatchType.QUERY:
                query_value = query_params.get(route.pattern)
                if query_value:
                    return RouteMatch(
                        route=route,
                        matched_pattern=query_value,
                    )

        return None

    async def proxy_request(
        self,
        route: RouteMatch,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Proxy request to target service.

        Args:
            route: Matched route
            path: Original request path
            method: HTTP method
            headers: Request headers
            body: Request body
            query_params: Query parameters

        Returns:
            Proxy response with status, headers, and body
        """
        import time
        start_time = time.time()

        # Build target URL
        target_path = path

        if route.match_type == RouteMatchType.PREFIX and route.strip_prefix:
            target_path = route.extracted_params.get("remaining_path", path)

        target_url = route.target_url.rstrip("/") + "/" + target_path.lstrip("/")

        # Add query params
        if query_params:
            import urllib.parse
            query_string = urllib.parse.urlencode(query_params)
            target_url += "?" + query_string

        # Get HTTP client
        client = self._get_client()

        try:
            # Prepare headers
            proxy_headers = {**headers, **route.headers}
            proxy_headers.pop("Host", None)  # Let client set Host

            # Make request
            response = await client.request(
                method=method,
                url=target_url,
                headers=proxy_headers,
                content=body,
                timeout=route.timeout,
            )

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "proxy_request_success",
                route=route.route.name,
                target_url=target_url,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.content,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "proxy_request_failed",
                route=route.route.name,
                target_url=target_url,
                error=str(e),
                duration_ms=duration_ms,
            )

            return {
                "status_code": 502,
                "headers": {},
                "body": b"Bad Gateway",
                "error": str(e),
                "duration_ms": duration_ms,
            }

    def _get_client(self) -> Any:
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global router
_router: Optional[APIRouter] = None


def get_router() -> APIRouter:
    """Get global API router."""
    global _router
    if _router is None:
        _router = APIRouter()
    return _router


async def route_request(
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    query_params: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Route a request using the global router.

    Args:
        path: Request path
        method: HTTP method
        headers: Request headers
        body: Request body
        query_params: Query parameters

    Returns:
        Proxy response if route found, None otherwise
    """
    router = get_router()
    route_match = router.match_route(path, method, headers, query_params)

    if route_match:
        return await router.proxy_request(
            route=route_match,
            path=path,
            method=method,
            headers=headers or {},
            body=body,
            query_params=query_params,
        )

    return None
