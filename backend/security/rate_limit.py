"""
Redis-based distributed rate limiting.

Provides:
- Sliding window rate limiting using Redis
- Per-IP and per-API-key rate limits
- Configurable time windows (minute, hour, day)
- Automatic cleanup of expired keys
- Support for multiple rate limit policies
"""

import time
from typing import Optional
from collections import defaultdict

from backend.logging_config import get_logger
from backend.cache import get_cache

logger = get_logger(__name__)


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis with sliding window algorithm.

    Supports multiple rate limit policies:
    - Per minute limits (for burst protection)
    - Per hour limits (for sustained usage)
    - Per day limits (for quota management)

    Uses Redis sorted sets for efficient sliding window implementation.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
    ):
        """
        Initialize Redis rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            requests_per_hour: Maximum requests per hour
            requests_per_day: Maximum requests per day
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.cache = get_cache()

        # For backwards compatibility, maintain in-memory fallback
        self.minute_window = defaultdict(list)
        self.hour_window = defaultdict(list)
        self.day_window = defaultdict(list)

    async def is_rate_limited(
        self,
        identifier: str,
        window: str = "minute"
    ) -> tuple[bool, Optional[int]]:
        """
        Check if the identifier has exceeded the rate limit.

        Args:
            identifier: Unique identifier (API key, IP address, etc.)
            window: Time window - "minute", "hour", or "day"

        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        current_time = time.time()
        cache_key = f"ratelimit:{window}:{identifier}"

        # Get the cache backend
        cache = get_cache()

        # Try Redis-based rate limiting
        try:
            result = await self._check_redis_rate_limit(cache, cache_key, window, identifier)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("redis_rate_limit_fallback", error=str(e))

        # Fall back to in-memory rate limiting
        return await self._check_memory_rate_limit(identifier, window, current_time)

    async def _check_redis_rate_limit(
        self,
        cache,
        cache_key: str,
        window: str,
        identifier: str
    ) -> Optional[tuple[bool, Optional[int]]]:
        """
        Check rate limit using Redis sorted set (sliding window).

        Args:
            cache: Cache backend
            cache_key: Redis key for rate limit data
            window: Time window
            identifier: Request identifier

        Returns:
            Tuple of (is_limited, retry_after) or None if Redis unavailable
        """
        # Check if using in-memory cache
        from backend.cache import InMemoryCache
        if isinstance(cache, InMemoryCache):
            return None

        current_time = time.time()

        # Define window parameters
        window_configs = {
            "minute": (60, self.requests_per_minute),
            "hour": (3600, self.requests_per_hour),
            "day": (86400, self.requests_per_day),
        }

        if window not in window_configs:
            return None

        window_seconds, max_requests = window_configs[window]
        window_start = current_time - window_seconds

        # Use Lua script for atomic check-and-increment
        lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local ttl = tonumber(ARGV[4])

            -- Remove entries outside the window
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

            -- Count current requests
            local current_count = redis.call('ZCARD', key)

            if current_count < max_requests then
                -- Add current request
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, ttl)
                return {0, current_count + 1, max_requests}
            else
                -- Get oldest request time for retry-after calculation
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                if #oldest > 0 then
                    local retry_after = math.ceil(oldest[1][2] + ttl - now)
                    if retry_after < 0 then
                        retry_after = 0
                    end
                    return {1, current_count, max_requests, retry_after}
                end
                return {1, current_count, max_requests, ttl}
            end
        """

        try:
            # Execute Lua script atomically
            result = await cache._client.eval(
                lua_script,
                1,
                cache_key,
                current_time,
                window_start,
                max_requests,
                window_seconds,
            )

            if result and result[0] == 0:
                # Not rate limited
                return False, None
            else:
                # Rate limited
                retry_after = result[3] if len(result) > 3 else window_seconds
                return True, int(retry_after)

        except Exception:
            return None

    async def _check_memory_rate_limit(
        self,
        identifier: str,
        window: str,
        current_time: float
    ) -> tuple[bool, Optional[int]]:
        """
        Check rate limit using in-memory storage (fallback).

        Args:
            identifier: Request identifier
            window: Time window
            current_time: Current timestamp

        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        window_configs = {
            "minute": (60, self.minute_window),
            "hour": (3600, self.hour_window),
            "day": (86400, self.day_window),
        }

        if window not in window_configs:
            return False, None

        window_seconds, window_store = window_configs[window]
        window_start = current_time - window_seconds

        # Clean old entries
        window_store[identifier] = [
            t for t in window_store[identifier] if t > window_start
        ]

        # Check if rate limited
        if len(window_store[identifier]) >= window_configs[window][0]:
            # Calculate retry after
            oldest_request = min(window_store[identifier])
            retry_after = int(oldest_request + window_seconds - current_time)
            if retry_after < 0:
                retry_after = 0
            return True, retry_after

        # Add current request
        window_store[identifier].append(current_time)
        return False, None

    async def get_rate_limit_status(
        self,
        identifier: str
    ) -> dict:
        """
        Get current rate limit status for an identifier.

        Args:
            identifier: API key or IP address

        Returns:
            Dictionary with current usage and limits
        """
        current_time = time.time()
        status = {
            "identifier": identifier,
            "limits": {},
        }

        for window_name, window_key in [("minute", "m"), ("hour", "h"), ("day", "d")]:
            cache_key = f"ratelimit:{window_name}:{identifier}"
            cache = get_cache()

            try:
                # Try Redis
                from backend.cache import InMemoryCache
                if not isinstance(cache, InMemoryCache):
                    count = await cache._client.zcard(cache_key)
                    limit = {
                        "minute": self.requests_per_minute,
                        "hour": self.requests_per_hour,
                        "day": self.requests_per_day,
                    }[window_name]

                    status["limits"][window_name] = {
                        "used": count,
                        "limit": limit,
                        "remaining": max(0, limit - count),
                    }
                    continue
            except Exception:
                pass

            # Fall back to in-memory
            window_configs = {
                "minute": (60, self.minute_window),
                "hour": (3600, self.hour_window),
                "day": (86400, self.day_window),
            }

            if window_name in window_configs:
                window_seconds, window_store = window_configs[window_name]
                window_start = current_time - window_seconds
                count = len([t for t in window_store.get(identifier, []) if t > window_start])
                limit = window_configs[window_name][0]

                status["limits"][window_name] = {
                    "used": count,
                    "limit": limit,
                    "remaining": max(0, limit - count),
                }

        return status

    async def reset_rate_limit(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Useful for admin operations or testing.

        Args:
            identifier: API key or IP address

        Returns:
            True if reset was successful
        """
        cache = get_cache()
        success = True

        # Clear in-memory windows
        self.minute_window.pop(identifier, None)
        self.hour_window.pop(identifier, None)
        self.day_window.pop(identifier, None)

        # Clear Redis keys
        for window in ["minute", "hour", "day"]:
            cache_key = f"ratelimit:{window}:{identifier}"
            try:
                await cache.delete(cache_key)
            except Exception:
                success = False

        return success


class RateLimitConfig:
    """Rate limit configuration."""

    # Default rate limits
    DEFAULT_REQUESTS_PER_MINUTE = 60
    DEFAULT_REQUESTS_PER_HOUR = 1000
    DEFAULT_REQUESTS_PER_DAY = 10000

    # Rate limits for different tiers
    RATE_LIMITS = {
        "free": {"minute": 10, "hour": 100, "day": 1000},
        "basic": {"minute": 30, "hour": 500, "day": 5000},
        "pro": {"minute": 100, "hour": 2000, "day": 20000},
        "enterprise": {"minute": 1000, "hour": 10000, "day": 100000},
    }

    @classmethod
    def get_limiter_for_tier(cls, tier: str = "free") -> RedisRateLimiter:
        """
        Get a rate limiter for a specific tier.

        Args:
            tier: Tier name (free, basic, pro, enterprise)

        Returns:
            Configured RedisRateLimiter
        """
        limits = cls.RATE_LIMITS.get(tier, cls.RATE_LIMITS["free"])
        return RedisRateLimiter(
            requests_per_minute=limits["minute"],
            requests_per_hour=limits["hour"],
            requests_per_day=limits["day"],
        )


# Global rate limiter instance
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RedisRateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        Global RedisRateLimiter configured from environment
    """
    global _rate_limiter
    if _rate_limiter is None:
        import os
        _rate_limiter = RedisRateLimiter(
            requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", str(RateLimitConfig.DEFAULT_REQUESTS_PER_MINUTE))),
            requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", str(RateLimitConfig.DEFAULT_REQUESTS_PER_HOUR))),
            requests_per_day=int(os.getenv("RATE_LIMIT_PER_DAY", str(RateLimitConfig.DEFAULT_REQUESTS_PER_DAY))),
        )
    return _rate_limiter
