"""
API Gateway features for request transformation and aggregation.

Provides:
- Request/response transformation
- API aggregation
- Request routing
- Proxy functionality
"""

from .transformer import RequestTransformer, ResponseTransformer, transform_request, transform_response
from .aggregator import APIAggregator, aggregate_responses
from .router import APIRouter, RouteConfig, route_request

__all__ = [
    "RequestTransformer",
    "ResponseTransformer",
    "transform_request",
    "transform_response",
    "APIAggregator",
    "aggregate_responses",
    "APIRouter",
    "RouteConfig",
    "route_request",
]
