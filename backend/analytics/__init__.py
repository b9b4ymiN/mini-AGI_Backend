"""
API Analytics and Usage Tracking Module.

Provides:
- Request tracking and metrics
- Usage analytics
- Performance monitoring
- Cost tracking (for LLM API calls)
- User behavior analysis
"""

from .tracker import (
    track_request,
    track_llm_request,
    track_error,
    get_usage_stats,
    get_performance_metrics,
    get_analytics_summary,
    AnalyticsTracker,
)

from .middleware import AnalyticsMiddleware

__all__ = [
    "track_request",
    "track_llm_request",
    "track_error",
    "get_usage_stats",
    "get_performance_metrics",
    "get_analytics_summary",
    "AnalyticsTracker",
    "AnalyticsMiddleware",
]
