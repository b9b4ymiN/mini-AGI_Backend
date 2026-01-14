"""
Integration tests for API endpoints.

Tests the full API with authentication, database, and LLM mocking.
"""

import pytest
from unittest.mock import patch

from backend.orchestrator.llm import LlmProviderError


@pytest.mark.asyncio
@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_health_endpoint(self, async_client):
        """Test /health endpoint returns 200."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_llm_info_endpoint(self, async_client):
        """Test /llm/info endpoint returns provider info."""
        response = await async_client.get("/llm/info")
        assert response.status_code == 200

        data = response.json()
        assert "provider" in data
        assert "model" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestPersonasEndpoint:
    """Tests for /personas endpoint."""

    async def test_personas_with_auth(self, async_client, auth_headers):
        """Test /personas with authentication."""
        response = await async_client.get("/personas", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "personas" in data
        assert isinstance(data["personas"], list)

    async def test_personas_without_auth(self, async_client):
        """Test /personas without authentication returns 401."""
        response = await async_client.get("/personas")
        assert response.status_code == 401

    async def test_personas_with_invalid_key(self, async_client):
        """Test /personas with invalid API key returns 403."""
        headers = {"X-API-Key": "invalid-key-12345"}
        response = await async_client.get("/personas", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.integration
class TestChatEndpoint:
    """Tests for /chat endpoint."""

    async def test_chat_with_auth(self, async_client, auth_headers, mock_llm_response, sample_chat_request):
        """Test /chat with authentication."""
        response = await async_client.post(
            "/chat",
            json=sample_chat_request,
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "events" in data
        assert "session_id" in data

    async def test_chat_without_auth(self, async_client, sample_chat_request):
        """Test /chat without authentication returns 401."""
        response = await async_client.post("/chat", json=sample_chat_request)
        assert response.status_code == 401

    async def test_chat_with_invalid_key(self, async_client, sample_chat_request):
        """Test /chat with invalid API key returns 403."""
        headers = {"X-API-Key": "invalid-key"}
        response = await async_client.post(
            "/chat",
            json=sample_chat_request,
            headers=headers
        )
        assert response.status_code == 403

    async def test_chat_with_persona(self, async_client, auth_headers, mock_llm_response):
        """Test /chat with persona parameter."""
        request = {
            "persona": "test-persona",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }

        response = await async_client.post(
            "/chat",
            json=request,
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_chat_with_session_id(self, async_client, auth_headers, mock_llm_response):
        """Test /chat with session_id parameter."""
        request = {
            "session_id": "test-session-123",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }

        response = await async_client.post(
            "/chat",
            json=request,
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        # Session ID should be preserved
        assert "session_id" in data

    async def test_chat_llm_error(self, async_client, auth_headers, mock_llm_error):
        """Test /chat handles LLM errors gracefully."""
        request = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }

        response = await async_client.post(
            "/chat",
            json=request,
            headers=auth_headers
        )
        # Should still return 200 with error message
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestSessionEndpoints:
    """Tests for session management endpoints."""

    async def test_create_session(self, async_client, auth_headers):
        """Test creating a new session."""
        response = await async_client.post(
            "/sessions",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 16

    async def test_create_session_without_auth(self, async_client):
        """Test creating session without auth returns 401."""
        response = await async_client.post("/sessions")
        assert response.status_code == 401

    async def test_get_session_info(self, async_client, auth_headers):
        """Test getting session information."""
        # Create a session first via API
        create_response = await async_client.post(
            "/sessions",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        response = await async_client.get(
            f"/sessions/{session_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == session_id

    async def test_get_session_info_not_found(self, async_client, auth_headers):
        """Test getting info for non-existent session returns 404."""
        response = await async_client.get(
            "/sessions/nonexistent-session",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_get_session_history(self, async_client, auth_headers):
        """Test getting session history."""
        # Create a session and add a conversation via chat
        chat_response = await async_client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
                ]
            },
            headers=auth_headers
        )
        assert chat_response.status_code == 200
        session_id = chat_response.json()["session_id"]

        response = await async_client.get(
            f"/sessions/{session_id}/history",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "history" in data
        # At least the conversation we just created
        assert len(data["history"]) >= 1

    async def test_search_conversations(self, async_client, auth_headers):
        """Test searching conversations."""
        # Create a conversation with specific content via chat
        chat_response = await async_client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Python programming"}]}
                ]
            },
            headers=auth_headers
        )
        assert chat_response.status_code == 200
        session_id = chat_response.json()["session_id"]

        response = await async_client.get(
            "/conversations/search",
            params={"query": "Python", "session_id": session_id},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestMemoryFactEndpoints:
    """Tests for memory fact endpoints."""

    async def test_save_memory_fact(self, async_client, auth_headers):
        """Test saving a memory fact."""
        response = await async_client.post(
            "/memory/facts",
            params={
                "fact_key": "language",
                "fact_value": "Thai",
                "fact_type": "preference",
                "user_id": "test-user"
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

    async def test_get_memory_facts(self, async_client, auth_headers):
        """Test getting memory facts."""
        # Save a fact first via API
        await async_client.post(
            "/memory/facts",
            params={
                "fact_key": "language",
                "fact_value": "Thai",
                "fact_type": "preference",
                "user_id": "test-user"
            },
            headers=auth_headers
        )

        response = await async_client.get(
            "/memory/facts",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "facts" in data
        assert len(data["facts"]) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestDatabaseManagementEndpoints:
    """Tests for database management endpoints (admin only)."""

    async def test_db_stats_with_admin_key(self, async_client, admin_headers):
        """Test /db/stats with admin key."""
        response = await async_client.get("/db/stats", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_conversations" in data
        assert "total_sessions" in data

    async def test_db_stats_with_regular_key(self, async_client, auth_headers):
        """Test /db/stats with regular key returns 403."""
        response = await async_client.get("/db/stats", headers=auth_headers)
        assert response.status_code == 403

    async def test_db_stats_without_auth(self, async_client):
        """Test /db/stats without auth returns 403."""
        response = await async_client.get("/db/stats")
        assert response.status_code == 403

    async def test_db_size_with_admin_key(self, async_client, admin_headers):
        """Test /db/size with admin key."""
        response = await async_client.get("/db/size", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "size_mb" in data

    async def test_db_status_with_admin_key(self, async_client, admin_headers):
        """Test /db/status with admin key."""
        response = await async_client.get("/db/status", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestRequestIDHeader:
    """Tests for X-Request-ID header."""

    async def test_request_id_generated(self, async_client, auth_headers):
        """Test that request ID is generated automatically."""
        response = await async_client.get("/personas", headers=auth_headers)
        assert response.status_code == 200

        # Check response has X-Request-ID header
        assert "x-request-id" in response.headers

    async def test_request_id_custom(self, async_client, auth_headers):
        """Test that custom request ID is preserved."""
        custom_id = "my-custom-request-id-123"
        headers = {
            **auth_headers,
            "X-Request-ID": custom_id
        }

        response = await async_client.get("/personas", headers=headers)
        assert response.status_code == 200

        # Check response has our custom request ID
        assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
@pytest.mark.integration
class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.slow
    async def test_rate_limit_enforcement(self, async_client, auth_headers):
        """Test that rate limiting is enforced."""
        # Make many rapid requests
        rate_limited = False
        for i in range(100):
            response = await async_client.get("/personas", headers=auth_headers)
            if response.status_code == 429:
                rate_limited = True
                break

        # Should eventually be rate limited
        assert rate_limited, "Rate limiting should be enforced"


@pytest.mark.asyncio
@pytest.mark.integration
class TestSecurityHeaders:
    """Tests for security headers."""

    async def test_security_headers_present(self, async_client):
        """Test that security headers are present."""
        response = await async_client.get("/health")

        headers = response.headers

        # Check for security headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in headers
        assert headers["x-frame-options"] == "DENY"

        assert "x-xss-protection" in headers

        assert "strict-transport-security" in headers

        assert "content-security-policy" in headers

        assert "permissions-policy" in headers
