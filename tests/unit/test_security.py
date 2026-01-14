"""
Unit tests for security module.

Tests authentication, rate limiting, and security middleware.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.security import (
    SecurityConfig,
    verify_api_key,
    should_bypass_auth,
    RateLimiter,
    require_admin,
)
from backend.security.auth import API_KEY_NAME, BYPASS_ENDPOINTS


class TestSecurityConfig:
    """Tests for SecurityConfig."""

    def test_default_config(self):
        """Test default security configuration."""
        assert SecurityConfig.RATE_LIMIT_PER_MINUTE == 60
        assert SecurityConfig.RATE_LIMIT_PER_HOUR == 1000
        assert SecurityConfig.MAX_REQUEST_SIZE == 10 * 1024 * 1024

    def test_api_keys_loaded(self):
        """Test that API keys are loaded from environment."""
        # Should have at least one API key from test environment
        assert len(SecurityConfig.VALID_API_KEYS) >= 1

    def test_admin_key_loaded(self):
        """Test that admin key is loaded."""
        assert SecurityConfig.ADMIN_API_KEY is not None
        assert len(SecurityConfig.ADMIN_API_KEY) > 0


class TestBypassAuth:
    """Tests for authentication bypass logic."""

    def test_bypass_health_endpoint(self):
        """Test that /health bypasses authentication."""
        request = MagicMock()
        request.url.path = "/health"
        assert should_bypass_auth(request) is True

    def test_bypass_docs_endpoint(self):
        """Test that /docs bypasses authentication."""
        request = MagicMock()
        request.url.path = "/docs"
        assert should_bypass_auth(request) is True

    def test_bypass_redoc_endpoint(self):
        """Test that /redoc bypasses authentication."""
        request = MagicMock()
        request.url.path = "/redoc"
        assert should_bypass_auth(request) is True

    def test_bypass_openapi_endpoint(self):
        """Test that /openapi.json bypasses authentication."""
        request = MagicMock()
        request.url.path = "/openapi.json"
        assert should_bypass_auth(request) is True

    def test_no_bypass_protected_endpoint(self):
        """Test that protected endpoints don't bypass authentication."""
        request = MagicMock()
        request.url.path = "/chat"
        assert should_bypass_auth(request) is False

    def test_no_bypass_personas_endpoint(self):
        """Test that /personas doesn't bypass authentication."""
        request = MagicMock()
        request.url.path = "/personas"
        assert should_bypass_auth(request) is False


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Get a rate limiter instance for testing."""
        return RateLimiter(requests_per_minute=10, requests_per_hour=100)

    def test_rate_limit_under_limit(self, limiter):
        """Test that requests under the limit are allowed."""
        allowed, _ = limiter.check_rate_limit("test-key")
        assert allowed is True

    def test_rate_limit_minute_limit(self, limiter):
        """Test minute limit enforcement."""
        # Make 10 requests (the limit)
        for _ in range(10):
            limiter.check_rate_limit("test-key-minute")

        # Next request should be blocked
        allowed, error = limiter.check_rate_limit("test-key-minute")
        assert allowed is False
        assert "Rate limit exceeded" in error

    def test_rate_limit_different_keys(self, limiter):
        """Test that rate limiting is per API key."""
        # Make 10 requests with key1
        for _ in range(10):
            limiter.check_rate_limit("key1")

        # key1 should be rate limited
        allowed1, _ = limiter.check_rate_limit("key1")
        assert allowed1 is False

        # key2 should still be allowed
        allowed2, _ = limiter.check_rate_limit("key2")
        assert allowed2 is True


@pytest.mark.asyncio
class TestVerifyAPIKey:
    """Tests for API key verification."""

    async def test_valid_api_key(self):
        """Test that valid API key is accepted."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.query_params = {}

        # Use a valid key from config
        valid_key = list(SecurityConfig.VALID_API_KEYS)[0]
        result = await verify_api_key(request, valid_key)
        assert result == valid_key

    async def test_missing_api_key(self):
        """Test that missing API key is rejected."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.query_params = {}

        with pytest.raises(HTTPException) as exc:
            await verify_api_key(request, None)

        assert exc.value.status_code == 401

    async def test_invalid_api_key(self):
        """Test that invalid API key is rejected."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.query_params = {}

        with pytest.raises(HTTPException) as exc:
            await verify_api_key(request, "invalid-key-12345")

        assert exc.value.status_code == 403

    async def test_admin_key_accepted(self):
        """Test that admin key is accepted."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.query_params = {}

        result = await verify_api_key(request, SecurityConfig.ADMIN_API_KEY)
        assert result == SecurityConfig.ADMIN_API_KEY


@pytest.mark.asyncio
class TestRequireAdmin:
    """Tests for admin-only access."""

    async def test_admin_key_accepted(self):
        """Test that admin key is accepted."""
        result = require_admin(SecurityConfig.ADMIN_API_KEY)
        assert result == SecurityConfig.ADMIN_API_KEY

    async def test_regular_key_rejected(self):
        """Test that regular API key is rejected."""
        regular_key = list(SecurityConfig.VALID_API_KEYS)[0]

        with pytest.raises(HTTPException) as exc:
            require_admin(regular_key)

        assert exc.value.status_code == 403
        assert "Admin privileges required" in str(exc.value.detail)

    async def test_invalid_key_rejected(self):
        """Test that invalid key is rejected."""
        with pytest.raises(HTTPException) as exc:
            require_admin("invalid-key")

        assert exc.value.status_code == 403
