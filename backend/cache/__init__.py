"""
Redis cache layer for LLM responses and frequently accessed data.

Provides:
- Redis connection management
- LLM response caching with TTL
- Session data caching
- Cache invalidation strategies
"""

import os
import json
import hashlib
import logging
from typing import Optional, Any, List
from functools import wraps
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    from redis.asyncio import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from backend.logging_config import get_logger

logger = get_logger(__name__)


# Cache configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true" and REDIS_AVAILABLE


class CacheBackend:
    """
    Abstract cache backend interface.

    Allows for different cache implementations (Redis, in-memory, etc.)
    """

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        raise NotImplementedError

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        raise NotImplementedError

    async def close(self):
        """Close cache connection."""
        raise NotImplementedError


class RedisCache(CacheBackend):
    """
    Redis cache backend implementation.

    Provides async Redis operations with connection pooling.
    """

    def __init__(self, url: str = REDIS_URL):
        """
        Initialize Redis cache.

        Args:
            url: Redis connection URL
        """
        self.url = url
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None

    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if self._client is None:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis package not installed. Install with: pip install redis")

            self._pool = ConnectionPool.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            )
            self._client = aioredis.Redis(connection_pool=self._pool)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not CACHE_ENABLED:
            return None

        try:
            await self._ensure_connection()
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        if not CACHE_ENABLED:
            return False

        try:
            await self._ensure_connection()
            serialized = json.dumps(value, default=str)
            if ttl is None:
                ttl = CACHE_TTL_SECONDS
            return await self._client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not CACHE_ENABLED:
            return False

        try:
            await self._ensure_connection()
            return await self._client.delete(key) > 0
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not CACHE_ENABLED:
            return 0

        try:
            await self._ensure_connection()
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("cache_delete_pattern_failed", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not CACHE_ENABLED:
            return False

        try:
            await self._ensure_connection()
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.warning("cache_exists_failed", key=key, error=str(e))
            return False

    async def close(self):
        """Close Redis connection."""
        if self._pool:
            await self._pool.aclose()  # Use aclose() instead of close()
            self._client = None
            self._pool = None


class InMemoryCache(CacheBackend):
    """
    In-memory cache backend for fallback/testing.

    Simple dictionary-based cache without persistence.
    """

    def __init__(self):
        """Initialize in-memory cache."""
        self._cache: dict = {}
        self._ttl: dict = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            if key in self._ttl:
                import time
                if time.time() > self._ttl[key]:
                    del self._cache[key]
                    del self._ttl[key]
                    return None
            return self._cache.get(key)
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        self._cache[key] = value
        if ttl:
            import time
            self._ttl[key] = time.time() + ttl
        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        return True

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (simple implementation)."""
        import fnmatch
        to_delete = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
        for key in to_delete:
            self._cache.pop(key, None)
            self._ttl.pop(key, None)
        return len(to_delete)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._cache

    async def close(self):
        """Clear cache."""
        self._cache.clear()
        self._ttl.clear()


# Global cache instance
_cache: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """
    Get the global cache instance.

    Returns:
        CacheBackend instance
    """
    global _cache
    if _cache is None:
        if REDIS_AVAILABLE and CACHE_ENABLED:
            _cache = RedisCache()
            logger.info("redis_cache_initialized")
        else:
            _cache = InMemoryCache()
            logger.info("in_memory_cache_initialized")
    return _cache


async def close_cache():
    """Close the cache connection."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None


# =============================================================================
# LLM Response Caching
# =============================================================================

def generate_llm_cache_key(
    prompt: str,
    system_instruction: str,
    model: str,
    persona: Optional[str] = None,
    temperature: float = 0.2
) -> str:
    """
    Generate cache key for LLM response.

    Args:
        prompt: User prompt
        system_instruction: System instruction
        model: Model name
        persona: Optional persona ID
        temperature: Temperature setting

    Returns:
        Cache key
    """
    # Create deterministic key from inputs
    key_data = f"{model}:{temperature}:{persona}:{system_instruction}:{prompt}"
    return f"llm:{hashlib.sha256(key_data.encode()).hexdigest()}"


async def get_cached_llm_response(
    prompt: str,
    system_instruction: str,
    model: str,
    persona: Optional[str] = None,
    temperature: float = 0.2
) -> Optional[str]:
    """
    Get cached LLM response if available.

    Args:
        prompt: User prompt
        system_instruction: System instruction
        model: Model name
        persona: Optional persona ID
        temperature: Temperature setting

    Returns:
        Cached response or None
    """
    cache = get_cache()
    key = generate_llm_cache_key(prompt, system_instruction, model, persona, temperature)
    result = await cache.get(key)
    if result:
        logger.info("llm_cache_hit", key=key[:16])
        return result.get("response")
    return None


async def cache_llm_response(
    prompt: str,
    response: str,
    system_instruction: str,
    model: str,
    persona: Optional[str] = None,
    temperature: float = 0.2,
    ttl: int = None
) -> bool:
    """
    Cache LLM response.

    Args:
        prompt: User prompt
        response: LLM response
        system_instruction: System instruction
        model: Model name
        persona: Optional persona ID
        temperature: Temperature setting
        ttl: Time to live in seconds

    Returns:
        True if cached successfully
    """
    cache = get_cache()
    key = generate_llm_cache_key(prompt, system_instruction, model, persona, temperature)
    value = {
        "response": response,
        "model": model,
        "persona": persona,
        "timestamp": __import__("time").time()
    }
    result = await cache.set(key, value, ttl)
    if result:
        logger.info("llm_cache_set", key=key[:16])
    return result


# =============================================================================
# Decorator for caching function results
# =============================================================================

def cached(
    key_prefix: str,
    ttl: int = None,
    key_builder: callable = None
):
    """
    Decorator for caching function results.

    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        key_builder: Optional function to build cache key from args

    Example:
        @cached("user_profile", ttl=300)
        async def get_user_profile(user_id: str):
            return await db.fetch_user(user_id)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key
            if key_builder:
                key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Simple key from args
                key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                key = f"{key_prefix}:{hashlib.sha256(':'.join(key_parts).encode()).hexdigest()}"

            # Try cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug("cache_hit", key=key[:32])
                return cached_result

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result, ttl)
            logger.debug("cache_miss", key=key[:32])

            return result
        return wrapper
    return decorator


# =============================================================================
# Cache Invalidation
# =============================================================================

async def invalidate_user_cache(user_id: str):
    """
    Invalidate all cache entries for a user.

    Args:
        user_id: User identifier
    """
    cache = get_cache()
    pattern = f"*user:{user_id}*"
    count = await cache.delete_pattern(pattern)
    logger.info("user_cache_invalidated", user_id=user_id, count=count)


async def invalidate_session_cache(session_id: str):
    """
    Invalidate all cache entries for a session.

    Args:
        session_id: Session identifier
    """
    cache = get_cache()
    pattern = f"*session:{session_id}*"
    count = await cache.delete_pattern(pattern)
    logger.info("session_cache_invalidated", session_id=session_id, count=count)


async def invalidate_persona_cache(persona_id: str):
    """
    Invalidate all cache entries for a persona.

    Args:
        persona_id: Persona identifier
    """
    cache = get_cache()
    pattern = f"*llm:*:{persona_id}:*"
    count = await cache.delete_pattern(pattern)
    logger.info("persona_cache_invalidated", persona_id=persona_id, count=count)


# =============================================================================
# Cache Statistics
# =============================================================================

async def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache stats
    """
    cache = get_cache()
    stats = {
        "type": "redis" if isinstance(cache, RedisCache) else "memory",
        "enabled": CACHE_ENABLED,
    }

    if isinstance(cache, RedisCache) and cache._client:
        try:
            info = await cache._client.info()
            stats.update({
                "connected": True,
                "memory_used": info.get("used_memory_human"),
                "total_keys": info.get("db0", {}).get("keys"),
                "hit_rate": "N/A",  # Would need to track hits/misses
            })
        except Exception as e:
            stats["connected"] = False
            stats["error"] = str(e)

    return stats
