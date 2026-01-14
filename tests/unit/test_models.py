"""
Unit tests for Pydantic models.

Tests request/response models for validation and serialization.
"""

import pytest
from pydantic import ValidationError

from backend.orchestrator.models import (
    ChatRequest,
    ChatResponse,
    OrchestratorEvent,
)


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_chat_request_valid(self):
        """Test valid chat request creation."""
        data = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }
        req = ChatRequest(**data)
        assert req.messages == data["messages"]
        assert req.persona is None
        assert req.session_id is None
        assert req.user_id is None

    def test_chat_request_with_persona(self):
        """Test chat request with persona."""
        data = {
            "persona": "test-persona",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }
        req = ChatRequest(**data)
        assert req.persona == "test-persona"

    def test_chat_request_with_session(self):
        """Test chat request with session ID."""
        data = {
            "session_id": "test-session-123",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }
        req = ChatRequest(**data)
        assert req.session_id == "test-session-123"

    def test_chat_request_with_user_id(self):
        """Test chat request with user ID."""
        data = {
            "user_id": "user-456",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ]
        }
        req = ChatRequest(**data)
        assert req.user_id == "user-456"

    def test_chat_request_empty_messages_accepted(self):
        """Test that empty messages array is accepted (Pydantic v2 behavior)."""
        # Pydantic v2 doesn't raise for empty lists by default
        req = ChatRequest(messages=[])
        assert req.messages == []

    def test_chat_request_missing_messages_fails(self):
        """Test that missing messages field fails validation."""
        with pytest.raises(ValidationError):
            ChatRequest(persona="test")


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_chat_response_valid(self):
        """Test valid chat response creation."""
        data = {
            "answer": "Test response",
            "events": [],
            "session_id": "session-123",
            "context_used": False
        }
        resp = ChatResponse(**data)
        assert resp.answer == "Test response"
        assert resp.events == []
        assert resp.session_id == "session-123"
        assert resp.context_used is False

    def test_chat_response_with_events(self):
        """Test chat response with orchestrator events."""
        data = {
            "answer": "Test response",
            "events": [
                {
                    "step": 1,
                    "agent": "orchestrator",
                    "action": "delegate",
                    "target_agent": "llm",
                    "thought": "Delegating to LLM"
                }
            ],
            "session_id": "session-123",
            "context_used": True
        }
        resp = ChatResponse(**data)
        assert len(resp.events) == 1
        assert resp.events[0].agent == "orchestrator"
        assert resp.context_used is True

    def test_chat_response_optional_fields(self):
        """Test chat response with optional fields."""
        resp = ChatResponse(answer="Test", events=[], session_id=None, context_used=False)
        assert resp.session_id is None


class TestOrchestratorEvent:
    """Tests for OrchestratorEvent model."""

    def test_orchestrator_event_minimal(self):
        """Test event with minimal fields."""
        event = OrchestratorEvent(
            step=1,
            agent="test-agent",
            action="test-action",
            thought="Test thought"
        )
        assert event.step == 1
        assert event.agent == "test-agent"
        assert event.action == "test-action"
        assert event.tool is None
        assert event.target_agent is None

    def test_orchestrator_event_with_tool(self):
        """Test event with tool usage."""
        event = OrchestratorEvent(
            step=1,
            agent="tool-user",
            action="use_tool",
            tool="search",
            thought="Searching for information"
        )
        assert event.tool == "search"

    def test_orchestrator_event_with_delegation(self):
        """Test event with agent delegation."""
        event = OrchestratorEvent(
            step=1,
            agent="orchestrator",
            action="delegate",
            target_agent="llm",
            thought="Delegating to LLM agent"
        )
        assert event.target_agent == "llm"
