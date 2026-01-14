"""
SQLAlchemy ORM models for the database.

Defines:
- Conversation model
- Session model
- MemoryFact model
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Integer,
    Float,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from . import Base


class Conversation(Base):
    """
    Conversation model for storing chat history.

    Represents a single turn in a conversation (user message + AI response).
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str] = mapped_column(Text, nullable=False)
    persona: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_conversations_session_timestamp", "session_id", "timestamp"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "persona": self.persona,
            "metadata": self.meta,
        }


class Session(Base):
    """
    Session model for tracking conversation sessions.

    Represents a conversation session with metadata.
    """

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "message_count": self.message_count,
            "metadata": self.meta,
        }


class MemoryFact(Base):
    """
    MemoryFact model for long-term user learning.

    Stores facts about users (preferences, skills, etc.) for personalization.
    """

    __tablename__ = "memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    fact_type: Mapped[str] = mapped_column(String(64), index=True)
    fact_key: Mapped[str] = mapped_column(String(256))
    fact_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    source_session: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Unique constraint: one fact per key per user
    __table_args__ = (
        UniqueConstraint("user_id", "fact_key", name="uq_user_fact"),
        Index("idx_memory_facts_confidence", "confidence"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "fact_type": self.fact_type,
            "fact_key": self.fact_key,
            "fact_value": self.fact_value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source_session": self.source_session,
        }
