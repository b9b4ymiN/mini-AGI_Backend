"""
Unit tests for database models and repository.

Tests SQLAlchemy models and async database operations.
"""

import pytest
from datetime import datetime

from backend.database.models import Conversation, Session, MemoryFact
from backend.database.repository import ConversationRepository


@pytest.mark.asyncio
@pytest.mark.db
class TestDatabaseModels:
    """Tests for database models."""

    async def test_conversation_model_creation(self, db_session):
        """Test creating a Conversation model."""
        conv = Conversation(
            session_id="test-session",
            user_id="test-user",
            user_message="Hello",
            ai_response="Hi there!",
            persona="test-persona"
        )
        db_session.add(conv)
        await db_session.flush()

        assert conv.id is not None
        assert conv.session_id == "test-session"
        assert conv.user_message == "Hello"

    async def test_session_model_creation(self, db_session):
        """Test creating a Session model."""
        session = Session(
            session_id="test-session-123",
            user_id="test-user",
            metadata={"test": "data"}
        )
        db_session.add(session)
        await db_session.flush()

        assert session.session_id == "test-session-123"
        assert session.message_count == 0

    async def test_memory_fact_model_creation(self, db_session):
        """Test creating a MemoryFact model."""
        # Use unique values to avoid UNIQUE constraint violations
        fact = MemoryFact(
            user_id="test-user-model",
            fact_type="preference",
            fact_key="test-language-key",
            fact_value="Thai",
            confidence=1.0
        )
        db_session.add(fact)
        await db_session.flush()

        assert fact.id is not None
        assert fact.fact_key == "test-language-key"

    async def test_conversation_to_dict(self, db_session):
        """Test Conversation.to_dict() method."""
        conv = Conversation(
            session_id="test-session",
            user_message="Hello",
            ai_response="Hi!"
        )
        db_session.add(conv)
        await db_session.flush()

        data = conv.to_dict()
        assert "id" in data
        assert "session_id" in data
        assert "timestamp" in data


@pytest.mark.asyncio
@pytest.mark.db
class TestConversationRepository:
    """Tests for ConversationRepository."""

    async def test_create_session(self, conversation_repo):
        """Test creating a new session."""
        session_id = await conversation_repo.create_session(user_id="test-user")

        assert session_id is not None
        assert len(session_id) == 16  # MD5 hash truncated to 16 chars

        # Verify session exists
        session = await conversation_repo.get_session(session_id)
        assert session is not None
        assert session["user_id"] == "test-user"

    async def test_get_or_create_session_new(self, conversation_repo):
        """Test get_or_create_session with no existing session."""
        session_id = await conversation_repo.get_or_create_session(
            session_id=None,
            user_id="test-user"
        )

        assert session_id is not None
        assert len(session_id) == 16

    async def test_get_or_create_session_existing(self, conversation_repo):
        """Test get_or_create_session with existing session."""
        # Create a session
        original_id = await conversation_repo.create_session(user_id="test-user")

        # Get the same session
        retrieved_id = await conversation_repo.get_or_create_session(
            session_id=original_id,
            user_id="test-user"
        )

        assert retrieved_id == original_id

    async def test_save_conversation(self, conversation_repo, test_session):
        """Test saving a conversation."""
        conv_id = await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="Hello",
            ai_response="Hi there!",
            user_id="test-user",
            persona="test-persona"
        )

        assert conv_id is not None
        assert isinstance(conv_id, int)

    async def test_get_conversation_history(self, conversation_repo, test_session):
        """Test retrieving conversation history."""
        # Save some conversations
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="Hello",
            ai_response="Hi!",
            user_id="test-user"
        )
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="How are you?",
            ai_response="Good!",
            user_id="test-user"
        )

        # Get history
        history = await conversation_repo.get_conversation_history(
            session_id=test_session,
            limit=10
        )

        assert len(history) == 2
        assert history[0]["user_message"] == "Hello"
        assert history[1]["user_message"] == "How are you?"

    async def test_conversation_history_chronological(self, conversation_repo, test_session):
        """Test that conversation history is in chronological order."""
        # Save conversations in sequence
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="First",
            ai_response="Response 1",
            user_id="test-user"
        )
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="Second",
            ai_response="Response 2",
            user_id="test-user"
        )

        history = await conversation_repo.get_conversation_history(
            session_id=test_session,
            limit=10
        )

        # Should be chronological (oldest first)
        assert history[0]["user_message"] == "First"
        assert history[1]["user_message"] == "Second"

    async def test_conversation_history_limit(self, conversation_repo, test_session):
        """Test conversation history limit."""
        # Save 5 conversations
        for i in range(5):
            await conversation_repo.save_conversation(
                session_id=test_session,
                user_message=f"Message {i}",
                ai_response=f"Response {i}",
                user_id="test-user"
            )

        # Get only 3
        history = await conversation_repo.get_conversation_history(
            session_id=test_session,
            limit=3
        )

        assert len(history) == 3

    async def test_search_conversations(self, conversation_repo, test_session):
        """Test searching conversations."""
        # Save conversations
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="I love Python programming",
            ai_response="Python is great!",
            user_id="test-user"
        )
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="JavaScript is also nice",
            ai_response="Yes, JavaScript is popular",
            user_id="test-user"
        )

        # Search for "Python"
        results = await conversation_repo.search_conversations(
            query="Python",
            session_id=test_session
        )

        assert len(results) == 1
        assert "Python" in results[0]["user_message"]

    async def test_save_memory_fact(self, conversation_repo):
        """Test saving a memory fact."""
        await conversation_repo.save_memory_fact(
            fact_key="language",
            fact_value="Thai",
            fact_type="preference",
            user_id="test-user",
            confidence=1.0
        )

        facts = await conversation_repo.get_memory_facts(user_id="test-user")
        assert len(facts) == 1
        assert facts[0]["fact_key"] == "language"
        assert facts[0]["fact_value"] == "Thai"

    async def test_update_memory_fact(self, conversation_repo):
        """Test updating an existing memory fact."""
        # Create fact
        await conversation_repo.save_memory_fact(
            fact_key="language",
            fact_value="English",
            fact_type="preference",
            user_id="test-user"
        )

        # Update fact
        await conversation_repo.save_memory_fact(
            fact_key="language",
            fact_value="Thai",
            fact_type="preference",
            user_id="test-user"
        )

        facts = await conversation_repo.get_memory_facts(user_id="test-user")
        assert facts[0]["fact_value"] == "Thai"

    async def test_get_session_stats(self, conversation_repo, test_session):
        """Test getting session statistics."""
        # Add a conversation
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="Hello",
            ai_response="Hi!",
            user_id="test-user"
        )

        stats = await conversation_repo.get_session_stats(test_session)

        assert stats["session_id"] == test_session
        assert stats["message_count"] == 1
        assert "created_at" in stats

    async def test_cleanup_old_sessions(self, conversation_repo):
        """Test cleaning up old sessions."""
        # Create an old session (simulated by not updating activity)
        old_session = await conversation_repo.create_session(user_id="old-user")

        # Clean up sessions older than 0 days (should delete all)
        deleted = await conversation_repo.cleanup_old_sessions(days=0)

        assert deleted >= 1

    async def test_get_db_stats(self, conversation_repo, test_session):
        """Test getting database statistics."""
        # Add some data
        await conversation_repo.save_conversation(
            session_id=test_session,
            user_message="Test",
            ai_response="Response",
            user_id="test-user"
        )

        stats = await conversation_repo.get_db_stats()

        assert "total_conversations" in stats
        assert "total_sessions" in stats
        assert "total_facts" in stats
        assert stats["total_conversations"] >= 1
