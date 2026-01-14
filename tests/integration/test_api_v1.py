"""
Integration tests for API v1 endpoints.

Tests versioned endpoints at /v1/* paths.
"""

import pytest

from backend.orchestrator.llm import LlmProviderError


@pytest.mark.asyncio
@pytest.mark.integration
class TestV1ChatEndpoints:
    """Tests for /v1/chat endpoint."""

    async def test_v1_chat_with_auth(self, async_client, auth_headers, mock_llm_response, sample_chat_request):
        """Test /v1/chat with authentication."""
        response = await async_client.post(
            "/v1/chat",
            json=sample_chat_request,
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "events" in data
        assert "session_id" in data

    async def test_v1_chat_with_persona(self, async_client, auth_headers, mock_llm_response):
        """Test /v1/chat with persona parameter."""
        request = {
            "persona": "test-persona",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }

        response = await async_client.post(
            "/v1/chat",
            json=request,
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_v1_chat_llm_error(self, async_client, auth_headers, mock_llm_error):
        """Test /v1/chat handles LLM errors gracefully."""
        request = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }

        response = await async_client.post(
            "/v1/chat",
            json=request,
            headers=auth_headers
        )
        # Should still return 200 with error message
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestV1PersonasEndpoints:
    """Tests for /v1/personas endpoint."""

    async def test_v1_personas_with_auth(self, async_client, auth_headers):
        """Test /v1/personas with authentication."""
        response = await async_client.get("/v1/personas", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "personas" in data
        assert isinstance(data["personas"], list)

    async def test_v1_personas_without_auth(self, async_client):
        """Test /v1/personas without authentication returns 401."""
        response = await async_client.get("/v1/personas")
        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
class TestV1SessionEndpoints:
    """Tests for /v1/sessions endpoints."""

    async def test_v1_create_session(self, async_client, auth_headers):
        """Test creating a new session."""
        response = await async_client.post(
            "/v1/sessions",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 16

    async def test_v1_get_session_info(self, async_client, auth_headers):
        """Test getting session information."""
        # Create a session first via API
        create_response = await async_client.post(
            "/v1/sessions",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        response = await async_client.get(
            f"/v1/sessions/{session_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == session_id

    async def test_v1_get_session_info_not_found(self, async_client, auth_headers):
        """Test getting info for non-existent session returns 404."""
        response = await async_client.get(
            "/v1/sessions/nonexistent-session",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_v1_get_session_history(self, async_client, auth_headers, mock_llm_response):
        """Test getting session history."""
        # Create a conversation via chat
        chat_response = await async_client.post(
            "/v1/chat",
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
            f"/v1/sessions/{session_id}/history",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "history" in data
        assert "count" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestV1MemoryEndpoints:
    """Tests for /v1/memory/* endpoints."""

    async def test_v1_save_memory_fact(self, async_client, auth_headers):
        """Test saving a memory fact."""
        response = await async_client.post(
            "/v1/memory/facts",
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

    async def test_v1_get_memory_facts(self, async_client, auth_headers):
        """Test getting memory facts."""
        # Save a fact first via API
        await async_client.post(
            "/v1/memory/facts",
            params={
                "fact_key": "language",
                "fact_value": "Thai",
                "fact_type": "preference",
                "user_id": "test-user"
            },
            headers=auth_headers
        )

        response = await async_client.get(
            "/v1/memory/facts",
            params={"user_id": "test-user"},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "facts" in data
        assert "count" in data

    async def test_v1_search_conversations(self, async_client, auth_headers, mock_llm_response):
        """Test searching conversations."""
        # Create a conversation with specific content
        chat_response = await async_client.post(
            "/v1/chat",
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
            "/v1/conversations/search",
            params={"query": "Python", "session_id": session_id},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "count" in data

    async def test_v1_cleanup_sessions(self, async_client, auth_headers):
        """Test cleaning up old sessions."""
        response = await async_client.delete(
            "/v1/sessions/cleanup",
            params={"days": 0},  # Clean up all sessions
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "deleted_count" in data
        assert "days" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestV1DatabaseEndpoints:
    """Tests for /v1/db/* endpoints (admin only)."""

    async def test_v1_db_stats_with_admin_key(self, async_client, admin_headers):
        """Test /v1/db/stats with admin key."""
        response = await async_client.get("/v1/db/stats", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_conversations" in data
        assert "total_sessions" in data

    async def test_v1_db_stats_with_regular_key(self, async_client, auth_headers):
        """Test /v1/db/stats with regular key returns 403."""
        response = await async_client.get("/v1/db/stats", headers=auth_headers)
        assert response.status_code == 403

    async def test_v1_db_size_with_admin_key(self, async_client, admin_headers):
        """Test /v1/db/size with admin key."""
        response = await async_client.get("/v1/db/size", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "size_mb" in data

    async def test_v1_db_status_with_admin_key(self, async_client, admin_headers):
        """Test /v1/db/status with admin key."""
        response = await async_client.get("/v1/db/status", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    async def test_v1_db_recommendations_with_admin(self, async_client, admin_headers):
        """Test /v1/db/recommendations with admin key."""
        response = await async_client.get("/v1/db/recommendations", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        # API returns a dict with "recommendations" key
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
@pytest.mark.integration
class TestAPIVersioning:
    """Tests for API versioning behavior."""

    async def test_v1_and_legacy_endpoints_both_work(self, async_client, auth_headers):
        """Test that both /v1 and legacy endpoints work."""
        # Test v1 endpoint
        v1_response = await async_client.get("/v1/personas", headers=auth_headers)
        assert v1_response.status_code == 200

        # Test legacy endpoint
        legacy_response = await async_client.get("/personas", headers=auth_headers)
        assert legacy_response.status_code == 200

        # Both should return same data
        assert v1_response.json() == legacy_response.json()

    async def test_v1_endpoints_use_prefix(self, async_client, auth_headers):
        """Test that v1 endpoints use /v1 prefix."""
        # Try without prefix (should still work for backward compatibility)
        response = await async_client.get("/personas", headers=auth_headers)
        assert response.status_code == 200

        # Try with prefix
        v1_response = await async_client.get("/v1/personas", headers=auth_headers)
        assert v1_response.status_code == 200
