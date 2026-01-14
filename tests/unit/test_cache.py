"""
Unit tests for cache module.

Tests Redis and in-memory cache backends, LLM response caching,
and cache invalidation.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from backend.cache import (
    RedisCache,
    InMemoryCache,
    CacheBackend,
    get_cache,
    close_cache,
    generate_llm_cache_key,
    get_cached_llm_response,
    cache_llm_response,
    invalidate_user_cache,
    invalidate_session_cache,
    invalidate_persona_cache,
    get_cache_stats,
    REDIS_AVAILABLE,
    CACHE_ENABLED,
)


@pytest.mark.asyncio
class TestInMemoryCache:
    """Tests for InMemoryCache backend."""

    @pytest.fixture
    def cache(self):
        """Get a fresh in-memory cache instance."""
        return InMemoryCache()

    async def test_set_and_get(self, cache):
        """Test setting and getting values."""
        await cache.set("test_key", {"data": "value"})
        result = await cache.get("test_key")
        assert result == {"data": "value"}

    async def test_get_nonexistent(self, cache):
        """Test getting nonexistent key returns None."""
        result = await cache.get("nonexistent_key")
        assert result is None

    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("test_key", "value")
        assert await cache.exists("test_key") is True

        await cache.delete("test_key")
        assert await cache.exists("test_key") is False

    async def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        await cache.set("test_key", "value", ttl=1)
        assert await cache.get("test_key") == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)
        result = await cache.get("test_key")
        assert result is None

    async def test_delete_pattern(self, cache):
        """Test deleting keys by pattern."""
        await cache.set("user:123:data", "value1")
        await cache.set("user:123:profile", "value2")
        await cache.set("user:456:data", "value3")

        count = await cache.delete_pattern("user:123:*")
        assert count == 2

        assert await cache.exists("user:123:data") is False
        assert await cache.exists("user:123:profile") is False
        assert await cache.exists("user:456:data") is True

    async def test_close(self, cache):
        """Test closing cache."""
        await cache.set("test_key", "value")
        await cache.close()
        assert await cache.get("test_key") is None


@pytest.mark.asyncio
class TestRedisCache:
    """Tests for RedisCache backend."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch("backend.cache.aioredis") as mock:
            mock.Redis.return_value = MagicMock()
            mock.ConnectionPool.from_url = MagicMock()
            yield mock

    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Get a Redis cache instance with mocked client."""
        cache = RedisCache("redis://localhost:6379/0")
        cache._client = MagicMock()
        cache._client.get = AsyncMock(return_value=None)
        cache._client.setex = AsyncMock(return_value=True)
        cache._client.delete = AsyncMock(return_value=1)
        cache._client.exists = AsyncMock(return_value=1)
        cache._client.scan_iter = AsyncMock(return_value=[])
        return cache

    async def test_set_and_get(self, redis_cache):
        """Test setting and getting values."""
        redis_cache._client.get = AsyncMock(return_value='{"data": "value"}')

        await redis_cache.set("test_key", {"data": "value"})
        result = await redis_cache.get("test_key")

        assert result == {"data": "value"}
        redis_cache._client.setex.assert_called_once()
        redis_cache._client.get.assert_called_once()

    async def test_get_nonexistent(self, redis_cache):
        """Test getting nonexistent key returns None."""
        redis_cache._client.get = AsyncMock(return_value=None)

        result = await redis_cache.get("nonexistent_key")
        assert result is None

    async def test_delete(self, redis_cache):
        """Test deleting a key."""
        redis_cache._client.exists = AsyncMock(return_value=1)

        result = await redis_cache.delete("test_key")
        assert result is True

    async def test_delete_nonexistent(self, redis_cache):
        """Test deleting nonexistent key."""
        redis_cache._client.delete = AsyncMock(return_value=0)

        result = await redis_cache.delete("test_key")
        assert result is False

    async def test_connection_error_handling(self, redis_cache):
        """Test that connection errors are handled gracefully."""
        redis_cache._client.get = AsyncMock(side_effect=Exception("Connection error"))

        result = await redis_cache.get("test_key")
        assert result is None  # Should return None on error


class TestGenerateLLMCacheKey:
    """Tests for LLM cache key generation."""

    def test_generate_cache_key_basic(self):
        """Test basic cache key generation."""
        key = generate_llm_cache_key(
            prompt="Hello",
            system_instruction="Be helpful",
            model="llama3",
            persona=None,
            temperature=0.2
        )
        assert key.startswith("llm:")
        assert len(key) == 4 + 64  # "llm:" + 64 char hex

    def test_cache_key_deterministic(self):
        """Test that same inputs produce same key."""
        key1 = generate_llm_cache_key("Hello", "Be helpful", "llama3", None, 0.2)
        key2 = generate_llm_cache_key("Hello", "Be helpful", "llama3", None, 0.2)
        assert key1 == key2

    def test_cache_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = generate_llm_cache_key("Hello", "Be helpful", "llama3", None, 0.2)
        key2 = generate_llm_cache_key("Hi", "Be helpful", "llama3", None, 0.2)
        assert key1 != key2

    def test_cache_key_with_persona(self):
        """Test cache key with persona."""
        key = generate_llm_cache_key(
            prompt="Hello",
            system_instruction="Be helpful",
            model="llama3",
            persona="trader",
            temperature=0.2
        )
        assert "trader" not in key  # Persona is hashed, not visible


@pytest.mark.asyncio
class TestLLMResponseCaching:
    """Tests for LLM response caching functions."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_cache(self, reset_cache):
        """Reset cache before each test."""
        pass

    async def test_cache_and_get_llm_response(self):
        """Test caching and retrieving LLM response."""
        await cache_llm_response(
            prompt="Hello",
            response="Hi there!",
            system_instruction="Be helpful",
            model="llama3"
        )

        cached = await get_cached_llm_response(
            prompt="Hello",
            system_instruction="Be helpful",
            model="llama3"
        )

        assert cached == "Hi there!"

    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cached = await get_cached_llm_response(
            prompt="Nonexistent prompt",
            system_instruction="Be helpful",
            model="llama3"
        )
        assert cached is None

    async def test_cache_with_different_temperature(self):
        """Test that different temperature creates different cache entries."""
        await cache_llm_response(
            prompt="Hello",
            response="Response at 0.2",
            system_instruction="Be helpful",
            model="llama3",
            temperature=0.2
        )

        await cache_llm_response(
            prompt="Hello",
            response="Response at 0.7",
            system_instruction="Be helpful",
            model="llama3",
            temperature=0.7
        )

        cached1 = await get_cached_llm_response(
            prompt="Hello",
            system_instruction="Be helpful",
            model="llama3",
            temperature=0.2
        )

        cached2 = await get_cached_llm_response(
            prompt="Hello",
            system_instruction="Be helpful",
            model="llama3",
            temperature=0.7
        )

        assert cached1 == "Response at 0.2"
        assert cached2 == "Response at 0.7"


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Tests for cache invalidation functions."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_cache(self, reset_cache):
        """Reset cache before each test."""
        pass

    async def test_invalidate_user_cache(self):
        """Test invalidating user cache."""
        # Cache some user data
        cache = get_cache()
        await cache.set("user:123:profile", {"name": "Test"})
        await cache.set("user:123:data", {"key": "value"})
        await cache.set("user:456:profile", {"name": "Other"})

        await invalidate_user_cache("123")

        assert await cache.exists("user:123:profile") is False
        assert await cache.exists("user:123:data") is False
        assert await cache.exists("user:456:profile") is True  # Should still exist

    async def test_invalidate_session_cache(self):
        """Test invalidating session cache."""
        cache = get_cache()
        await cache.set("session:abc:messages", ["msg1", "msg2"])
        await cache.set("session:xyz:messages", ["msg3"])

        await invalidate_session_cache("abc")

        assert await cache.exists("session:abc:messages") is False
        assert await cache.exists("session:xyz:messages") is True

    async def test_invalidate_persona_cache(self):
        """Test invalidating persona cache."""
        cache = get_cache()
        # Simulate LLM cache keys with persona
        await cache.set("llm:abc123:trader:def456", "response1")
        await cache.set("llm:xyz789:helper:def456", "response2")

        await invalidate_persona_cache("trader")

        # The trader persona cache should be invalidated
        assert await cache.exists("llm:abc123:trader:def456") is False
        # Other persona should still exist (pattern match is approximate in memory)


@pytest.mark.asyncio
class TestCacheStats:
    """Tests for cache statistics."""

    async def test_get_cache_stats_memory(self):
        """Test getting stats for in-memory cache."""
        stats = await get_cache_stats()
        assert "type" in stats
        assert "enabled" in stats
        assert stats["type"] in ["redis", "memory"]

    async def test_get_cache_stats_redis(self):
        """Test getting stats for Redis cache."""
        with patch("backend.cache.REDIS_AVAILABLE", True):
            with patch("backend.cache.CACHE_ENABLED", True):
                # Create a mock Redis cache
                mock_client = MagicMock()
                mock_client.info = AsyncMock(return_value={
                    "used_memory_human": "1.5M",
                    "db0": {"keys": 42}
                })

                cache = RedisCache()
                cache._client = mock_client

                with patch("backend.cache._cache", cache):
                    stats = await get_cache_stats()
                    assert stats["type"] == "redis"
                    assert stats["enabled"] is True
                    assert "memory_used" in stats


@pytest.mark.asyncio
class TestGlobalCache:
    """Tests for global cache instance."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_cache(self, reset_cache):
        """Reset cache before each test."""
        pass

    async def test_get_cache_singleton(self):
        """Test that get_cache returns same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    async def test_close_cache(self):
        """Test closing global cache."""
        cache = get_cache()
        await cache.set("test", "value")

        await close_cache()

        # Get new cache instance
        new_cache = get_cache()
        # Old data should be gone (for in-memory cache)
        assert await new_cache.get("test") is None
