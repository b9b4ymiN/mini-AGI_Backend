"""
Async database repository for conversation memory.

Provides async database operations for:
- Session management
- Conversation storage
- Context retrieval
- Memory facts
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import logging

from .models import Conversation, Session, MemoryFact

logger = logging.getLogger(__name__)


class ConversationRepository:
    """
    Repository for conversation and session management.

    Provides async CRUD operations for conversations and sessions.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    # ========================================================================
    # Session Management
    # ========================================================================

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation session.

        Args:
            user_id: Optional user identifier
            metadata: Optional session metadata

        Returns:
            New session ID
        """
        # Generate session ID
        timestamp = datetime.now().isoformat()
        session_id = hashlib.md5(f"{user_id}_{timestamp}".encode()).hexdigest()[:16]

        # Create session
        session = Session(
            session_id=session_id,
            user_id=user_id,
            meta=metadata or {"created": timestamp}
        )

        self.db.add(session)
        await self.db.flush()

        logger.debug(f"Created session: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session dict or None if not found
        """
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            return session.to_dict()
        return None

    async def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional existing session ID
            user_id: Optional user identifier

        Returns:
            Session ID
        """
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session_id

        return await self.create_session(user_id)

    async def update_session_activity(self, session_id: str) -> None:
        """
        Update last activity timestamp and message count for session.

        Args:
            session_id: Session identifier
        """
        await self.db.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(
                last_activity=datetime.utcnow(),
                message_count=Session.message_count + 1
            )
        )

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics
        """
        # Get session info
        session_result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            return {}

        # Get message count
        count_result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.session_id == session_id)
        )
        message_count = count_result.scalar()

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "message_count": message_count,
            "metadata": session.metadata or {},
        }

    # ========================================================================
    # Conversation Storage
    # ========================================================================

    async def save_conversation(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        user_id: Optional[str] = None,
        persona: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save a conversation turn to database.

        Args:
            session_id: Session identifier
            user_message: User's message
            ai_response: AI's response
            user_id: Optional user identifier
            persona: Optional persona used
            metadata: Optional additional metadata

        Returns:
            Conversation ID
        """
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response,
            persona=persona,
            meta=metadata
        )

        self.db.add(conversation)
        await self.db.flush()

        # Update session activity
        await self.update_session_activity(session_id)

        logger.debug(f"Saved conversation {conversation.id} for session {session_id}")
        return conversation.id

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10,
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            include_metadata: Whether to include metadata

        Returns:
            List of conversation turns (chronological order)
        """
        query = select(Conversation).where(
            Conversation.session_id == session_id
        ).order_by(Conversation.id.desc()).limit(limit)

        result = await self.db.execute(query)
        conversations = result.scalars().all()

        # Convert to dicts and reverse to chronological order
        history = [
            conv.to_dict() for conv in reversed(conversations)
        ]

        if not include_metadata:
            for item in history:
                item.pop("metadata", None)

        return history

    async def get_recent_context(
        self,
        session_id: str,
        max_turns: int = 5,
        max_chars: int = 2000
    ) -> str:
        """
        Get recent conversation context as formatted string.

        Args:
            session_id: Session identifier
            max_turns: Maximum conversation turns to include
            max_chars: Maximum total characters

        Returns:
            Formatted context string
        """
        history = await self.get_conversation_history(session_id, limit=max_turns)

        if not history:
            return ""

        context_parts = []
        total_chars = 0

        for turn in history:
            turn_text = f"User: {turn['user_message']}\nAI: {turn['ai_response']}\n"
            turn_chars = len(turn_text)

            if total_chars + turn_chars > max_chars:
                break

            context_parts.append(turn_text)
            total_chars += turn_chars

        if context_parts:
            return "Previous conversation:\n" + "\n".join(context_parts)

        return ""

    async def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by text content.

        Args:
            query: Search query
            user_id: Optional filter by user
            session_id: Optional filter by session
            limit: Maximum results

        Returns:
            List of matching conversations
        """
        # Build search query
        conditions = [
            or_(
                Conversation.user_message.ilike(f"%{query}%"),
                Conversation.ai_response.ilike(f"%{query}%")
            )
        ]

        if user_id:
            conditions.append(Conversation.user_id == user_id)

        if session_id:
            conditions.append(Conversation.session_id == session_id)

        stmt = select(Conversation).where(
            and_(*conditions)
        ).order_by(Conversation.timestamp.desc()).limit(limit)

        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        return [conv.to_dict() for conv in conversations]

    # ========================================================================
    # Memory Facts
    # ========================================================================

    async def save_memory_fact(
        self,
        fact_key: str,
        fact_value: str,
        fact_type: str = "general",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> None:
        """
        Save a learned fact to long-term memory.

        Uses upsert (insert or update on conflict).

        Args:
            fact_key: Unique key for the fact
            fact_value: The fact content
            fact_type: Type of fact (preference, fact, skill, etc.)
            user_id: Optional user identifier
            session_id: Source session
            confidence: Confidence level (0.0 - 1.0)
        """
        # Check if fact exists
        result = await self.db.execute(
            select(MemoryFact).where(
                and_(
                    MemoryFact.user_id == user_id,
                    MemoryFact.fact_key == fact_key
                )
            )
        )
        existing_fact = result.scalar_one_or_none()

        if existing_fact:
            # Update existing fact
            existing_fact.fact_value = fact_value
            existing_fact.confidence = confidence
            existing_fact.updated_at = datetime.utcnow()
            existing_fact.source_session = session_id
        else:
            # Insert new fact
            new_fact = MemoryFact(
                user_id=user_id,
                fact_type=fact_type,
                fact_key=fact_key,
                fact_value=fact_value,
                confidence=confidence,
                source_session=session_id
            )
            self.db.add(new_fact)

        logger.debug(f"Saved memory fact: {fact_key} for user {user_id}")

    async def get_memory_facts(
        self,
        user_id: Optional[str] = None,
        fact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memory facts.

        Args:
            user_id: Optional filter by user
            fact_type: Optional filter by type

        Returns:
            List of memory facts
        """
        conditions = []

        if user_id:
            conditions.append(MemoryFact.user_id == user_id)

        if fact_type:
            conditions.append(MemoryFact.fact_type == fact_type)

        stmt = select(MemoryFact).where(
            and_(*conditions) if conditions else True
        ).order_by(
            MemoryFact.confidence.desc(),
            MemoryFact.updated_at.desc()
        )

        result = await self.db.execute(stmt)
        facts = result.scalars().all()

        return [fact.to_dict() for fact in facts]

    async def format_memory_facts(self, user_id: Optional[str] = None) -> str:
        """
        Format memory facts as context string.

        Args:
            user_id: Optional user identifier

        Returns:
            Formatted facts string
        """
        facts = await self.get_memory_facts(user_id)

        if not facts:
            return ""

        fact_lines = [f"- {fact['fact_key']}: {fact['fact_value']}" for fact in facts]
        return "Known facts about user:\n" + "\n".join(fact_lines)

    # ========================================================================
    # Cleanup & Maintenance
    # ========================================================================

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get old session IDs
        session_result = await self.db.execute(
            select(Session.session_id).where(Session.last_activity < cutoff_date)
        )
        old_session_ids = [row[0] for row in session_result.fetchall()]

        if not old_session_ids:
            return 0

        # Delete conversations for old sessions
        conv_result = await self.db.execute(
            delete(Conversation).where(
                Conversation.session_id.in_(old_session_ids)
            )
        )

        # Delete old sessions
        session_result = await self.db.execute(
            delete(Session).where(Session.last_activity < cutoff_date)
        )

        deleted_count = session_result.rowcount
        logger.info(f"Cleaned up {deleted_count} old sessions (older than {days} days)")

        return deleted_count

    async def get_db_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        # Count conversations
        conv_count = await self.db.execute(select(func.count(Conversation.id)))
        total_conversations = conv_count.scalar()

        # Count sessions
        sess_count = await self.db.execute(select(func.count(Session.session_id)))
        total_sessions = sess_count.scalar()

        # Count facts
        fact_count = await self.db.execute(select(func.count(MemoryFact.id)))
        total_facts = fact_count.scalar()

        # Get date range
        oldest_result = await self.db.execute(
            select(func.min(Conversation.timestamp))
        )
        oldest_conversation = oldest_result.scalar()

        newest_result = await self.db.execute(
            select(func.max(Conversation.timestamp))
        )
        newest_conversation = newest_result.scalar()

        # Count unique users
        unique_users_result = await self.db.execute(
            select(func.count(func.distinct(Conversation.user_id))).where(
                Conversation.user_id.isnot(None)
            )
        )
        unique_users = unique_users_result.scalar()

        return {
            "total_conversations": total_conversations or 0,
            "total_sessions": total_sessions or 0,
            "total_facts": total_facts or 0,
            "oldest_conversation": oldest_conversation.isoformat() if oldest_conversation else None,
            "newest_conversation": newest_conversation.isoformat() if newest_conversation else None,
            "unique_users": unique_users or 0,
        }
