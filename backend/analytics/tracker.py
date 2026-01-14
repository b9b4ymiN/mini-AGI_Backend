"""
Request and usage tracking for API analytics.

Provides:
- Request tracking middleware
- LLM usage tracking
- Error tracking
- Performance metrics
- Usage statistics
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from backend.logging_config import get_logger
from backend.cache import get_cache

logger = get_logger(__name__)


@dataclass
class RequestMetric:
    """Individual request metric."""
    timestamp: float
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    persona: Optional[str] = None
    model: Optional[str] = None
    tokens_used: int = 0
    cached: bool = False
    error: Optional[str] = None


@dataclass
class UsageStats:
    """Usage statistics for a time period."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    total_tokens_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    unique_users: int = 0
    top_personas: Dict[str, int] = field(default_factory=dict)
    top_models: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)


class AnalyticsTracker:
    """
    Central analytics tracker for API usage and performance.

    Tracks:
    - Request counts and rates
    - Response times
    - LLM token usage
    - Cache hit rates
    - Error rates
    - User behavior patterns
    """

    def __init__(self):
        """Initialize analytics tracker."""
        self.cache = get_cache()
        self._in_memory_metrics: List[RequestMetric] = []
        self._max_memory_metrics = 10000

    async def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Track a single API request.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            user_id: Optional user identifier
            api_key: Optional API key hash
            error: Optional error message
        """
        metric = RequestMetric(
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            user_id=user_id,
            api_key=api_key,
            error=error,
        )

        # Store in memory
        self._in_memory_metrics.append(metric)
        if len(self._in_memory_metrics) > self._max_memory_metrics:
            self._in_memory_metrics.pop(0)

        # Store in cache for persistence
        cache_key = f"analytics:request:{int(metric.timestamp)}:{endpoint}:{method}"
        await self.cache.set(cache_key, metric, ttl=86400)  # 24 hours

    async def track_llm_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        persona: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: int = 0,
        cached: bool = False,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Track an LLM API request with additional metadata.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            persona: Persona used (if any)
            model: LLM model used
            tokens_used: Number of tokens consumed
            cached: Whether response was from cache
            user_id: Optional user identifier
            api_key: Optional API key hash
        """
        metric = RequestMetric(
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            user_id=user_id,
            api_key=api_key,
            persona=persona,
            model=model,
            tokens_used=tokens_used,
            cached=cached,
        )

        # Store in memory
        self._in_memory_metrics.append(metric)
        if len(self._in_memory_metrics) > self._max_memory_metrics:
            self._in_memory_metrics.pop(0)

        # Store in cache
        cache_key = f"analytics:llm:{int(metric.timestamp)}:{endpoint}"
        await self.cache.set(cache_key, metric, ttl=86400)

        # Update aggregate counters
        self._update_counters(metric)

    def track_error(
        self,
        endpoint: str,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Track an error occurrence.

        Args:
            endpoint: API endpoint where error occurred
            error_type: Type of error (e.g., "rate_limit_exceeded", "llm_error")
            error_message: Error message
            user_id: Optional user identifier
            api_key: Optional API key hash
        """
        cache_key = f"analytics:error:{error_type}:{int(time.time())}"
        error_data = {
            "endpoint": endpoint,
            "error_type": error_type,
            "error_message": error_message,
            "user_id": user_id,
            "api_key": api_key,
            "timestamp": time.time(),
        }
        self.cache.set(cache_key, error_data, ttl=86400)

        # Update error counter
        counter_key = f"analytics:errors:{error_type}"
        try:
            current = self.cache.get(counter_key) or 0
            self.cache.set(counter_key, current + 1, ttl=3600)
        except Exception:
            pass

    def _update_counters(self, metric: RequestMetric) -> None:
        """Update aggregate counters for a metric."""
        # Update request counters
        counter_key = f"analytics:requests:{metric.endpoint}"
        try:
            current = self.cache.get(counter_key) or 0
            self.cache.set(counter_key, current + 1, ttl=3600)
        except Exception:
            pass

        # Update token counter
        if metric.tokens_used > 0:
            token_key = f"analytics:tokens:{metric.model or 'unknown'}"
            try:
                current = self.cache.get(token_key) or 0
                self.cache.set(token_key, current + metric.tokens_used, ttl=3600)
            except Exception:
                pass

        # Update cache counters
        cache_key = f"analytics:cache:{'hit' if metric.cached else 'miss'}"
        try:
            current = self.cache.get(cache_key) or 0
            self.cache.set(cache_key, current + 1, ttl=3600)
        except Exception:
            pass

    def get_usage_stats(self, hours: int = 1) -> UsageStats:
        """
        Get usage statistics for the specified time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            UsageStats with aggregated statistics
        """
        cutoff_time = time.time() - (hours * 3600)

        # Filter metrics from memory
        recent_metrics = [
            m for m in self._in_memory_metrics
            if m.timestamp > cutoff_time
        ]

        stats = UsageStats()

        if not recent_metrics:
            return stats

        # Calculate statistics
        stats.total_requests = len(recent_metrics)
        stats.successful_requests = sum(1 for m in recent_metrics if 200 <= m.status_code < 400)
        stats.failed_requests = stats.total_requests - stats.successful_requests

        response_times = [m.response_time_ms for m in recent_metrics]
        stats.avg_response_time_ms = sum(response_times) / len(response_times)

        stats.total_tokens_used = sum(m.tokens_used for m in recent_metrics)
        stats.cache_hits = sum(1 for m in recent_metrics if m.cached)
        stats.cache_misses = stats.total_requests - stats.cache_hits

        # Unique users
        unique_users = {m.user_id for m in recent_metrics if m.user_id}
        stats.unique_users = len(unique_users)

        # Top personas
        personas = defaultdict(int)
        for m in recent_metrics:
            if m.persona:
                personas[m.persona] += 1
        stats.top_personas = dict(sorted(personas.items(), key=lambda x: x[1], reverse=True)[:10])

        # Top models
        models = defaultdict(int)
        for m in recent_metrics:
            if m.model:
                models[m.model] += 1
        stats.top_models = dict(sorted(models.items(), key=lambda x: x[1], reverse=True)[:10])

        return stats

    def get_performance_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get performance metrics for the specified time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with performance metrics
        """
        stats = self.get_usage_stats(hours)

        return {
            "period_hours": hours,
            "requests": {
                "total": stats.total_requests,
                "successful": stats.successful_requests,
                "failed": stats.failed_requests,
                "success_rate": stats.successful_requests / stats.total_requests if stats.total_requests > 0 else 0,
                "per_minute": stats.total_requests / hours / 60,
            },
            "performance": {
                "avg_response_time_ms": stats.avg_response_time_ms,
                "p50_ms": self._percentile([m.response_time_ms for m in self._get_recent_metrics(hours)], 50),
                "p95_ms": self._percentile([m.response_time_ms for m in self._get_recent_metrics(hours)], 95),
                "p99_ms": self._percentile([m.response_time_ms for m in self._get_recent_metrics(hours)], 99),
            },
            "tokens": {
                "total_used": stats.total_tokens_used,
                "avg_per_request": stats.total_tokens_used / stats.total_requests if stats.total_requests > 0 else 0,
            },
            "cache": {
                "hits": stats.cache_hits,
                "misses": stats.cache_misses,
                "hit_rate": stats.cache_hits / (stats.cache_hits + stats.cache_misses) if (stats.cache_hits + stats.cache_misses) > 0 else 0,
            },
            "users": {
                "unique": stats.unique_users,
            },
        }

    def get_analytics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get a comprehensive analytics summary.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with complete analytics summary
        """
        stats = self.get_usage_stats(hours)
        performance = self.get_performance_metrics(hours)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "hours": hours,
                "start": (datetime.utcnow() - timedelta(hours=hours)).isoformat(),
                "end": datetime.utcnow().isoformat(),
            },
            "usage": stats.__dict__,
            "performance": performance,
            "top_personas": stats.top_personas,
            "top_models": stats.top_models,
        }

    def _get_recent_metrics(self, hours: int) -> List[RequestMetric]:
        """Get metrics from the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        return [m for m in self._in_memory_metrics if m.timestamp > cutoff_time]

    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile of a list of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


# Global tracker instance
_tracker: Optional[AnalyticsTracker] = None


def get_tracker() -> AnalyticsTracker:
    """Get the global analytics tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = AnalyticsTracker()
    return _tracker


async def track_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Track an API request using the global tracker."""
    await get_tracker().track_request(endpoint, method, status_code, response_time_ms, user_id, api_key, error)


async def track_llm_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    persona: Optional[str] = None,
    model: Optional[str] = None,
    tokens_used: int = 0,
    cached: bool = False,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """Track an LLM API request using the global tracker."""
    await get_tracker().track_llm_request(endpoint, method, status_code, response_time_ms, persona, model, tokens_used, cached, user_id, api_key)


def track_error(
    endpoint: str,
    error_type: str,
    error_message: str,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """Track an error using the global tracker."""
    get_tracker().track_error(endpoint, error_type, error_message, user_id, api_key)


def get_usage_stats(hours: int = 1) -> UsageStats:
    """Get usage statistics using the global tracker."""
    return get_tracker().get_usage_stats(hours)


def get_performance_metrics(hours: int = 1) -> Dict[str, Any]:
    """Get performance metrics using the global tracker."""
    return get_tracker().get_performance_metrics(hours)


def get_analytics_summary(hours: int = 24) -> Dict[str, Any]:
    """Get analytics summary using the global tracker."""
    return get_tracker().get_analytics_summary(hours)
