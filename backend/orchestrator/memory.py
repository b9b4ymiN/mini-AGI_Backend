"""
Conversation memory and context management system.

This module provides:
- Conversation history storage (SQLite)
- Context retrieval and summarization
- Session management
- Memory cleanup and optimization
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import hashlib


# Database path
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "conversations.db"


# ============================================================================
# Database Initialization
# ============================================================================

def init_db():
    """Initialize the conversation database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            persona TEXT,
            metadata TEXT
        )
    """)

    # Create indexes for conversations table
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)
    """)

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0,
            metadata TEXT
        )
    """)

    # Memory facts table (for long-term learning)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            fact_type TEXT,
            fact_key TEXT,
            fact_value TEXT,
            confidence REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            source_session TEXT,
            UNIQUE(user_id, fact_key)
        )
    """)

    conn.commit()
    conn.close()


# Initialize database on module load
init_db()


# ============================================================================
# Session Management
# ============================================================================

def create_session(user_id: Optional[str] = None) -> str:
    """
    Create a new conversation session.

    Args:
        user_id: Optional user identifier

    Returns:
        New session ID
    """
    # Generate session ID
    timestamp = datetime.now().isoformat()
    session_id = hashlib.md5(f"{user_id}_{timestamp}".encode()).hexdigest()[:16]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sessions (session_id, user_id, metadata)
        VALUES (?, ?, ?)
    """, (session_id, user_id, json.dumps({"created": timestamp})))

    conn.commit()
    conn.close()

    return session_id


def get_or_create_session(session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """
    Get existing session or create new one.

    Args:
        session_id: Optional existing session ID
        user_id: Optional user identifier

    Returns:
        Session ID
    """
    if session_id:
        # Check if session exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return session_id

    # Create new session
    return create_session(user_id)


def update_session_activity(session_id: str):
    """Update last activity timestamp for session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sessions
        SET last_activity = CURRENT_TIMESTAMP,
            message_count = message_count + 1
        WHERE session_id = ?
    """, (session_id,))

    conn.commit()
    conn.close()


# ============================================================================
# Conversation Storage
# ============================================================================

def save_conversation(
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversations (session_id, user_id, user_message, ai_response, persona, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        user_id,
        user_message,
        ai_response,
        persona,
        json.dumps(metadata) if metadata else None
    ))

    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Update session activity
    update_session_activity(session_id)

    return conversation_id


# ============================================================================
# Context Retrieval
# ============================================================================

def get_conversation_history(
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
        List of conversation turns
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if include_metadata:
        query = """
            SELECT id, timestamp, user_message, ai_response, persona, metadata
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
    else:
        query = """
            SELECT id, timestamp, user_message, ai_response, persona
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

    cursor.execute(query, (session_id, limit))
    rows = cursor.fetchall()
    conn.close()

    # Convert to list of dicts (reverse to chronological order)
    history = []
    for row in reversed(rows):
        item = dict(row)
        if include_metadata and item.get("metadata"):
            item["metadata"] = json.loads(item["metadata"])
        history.append(item)

    return history


def get_recent_context(
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
    history = get_conversation_history(session_id, limit=max_turns)

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


def search_conversations(
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = """
        SELECT id, session_id, timestamp, user_message, ai_response, persona
        FROM conversations
        WHERE (user_message LIKE ? OR ai_response LIKE ?)
    """
    params = [f"%{query}%", f"%{query}%"]

    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)

    if session_id:
        sql += " AND session_id = ?"
        params.append(session_id)

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ============================================================================
# Memory Facts (Long-term Learning)
# ============================================================================

def save_memory_fact(
    fact_key: str,
    fact_value: str,
    fact_type: str = "general",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    confidence: float = 1.0
):
    """
    Save a learned fact to long-term memory.

    Args:
        fact_key: Unique key for the fact
        fact_value: The fact content
        fact_type: Type of fact (preference, fact, skill, etc.)
        user_id: Optional user identifier
        session_id: Source session
        confidence: Confidence level (0.0 - 1.0)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO memory_facts (user_id, fact_type, fact_key, fact_value, confidence, source_session)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, fact_key) DO UPDATE SET
            fact_value = excluded.fact_value,
            confidence = excluded.confidence,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, fact_type, fact_key, fact_value, confidence, session_id))

    conn.commit()
    conn.close()


def get_memory_facts(
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = "SELECT * FROM memory_facts WHERE 1=1"
    params = []

    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)

    if fact_type:
        sql += " AND fact_type = ?"
        params.append(fact_type)

    sql += " ORDER BY confidence DESC, updated_at DESC"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def format_memory_facts(user_id: Optional[str] = None) -> str:
    """
    Format memory facts as context string.

    Args:
        user_id: Optional user identifier

    Returns:
        Formatted facts string
    """
    facts = get_memory_facts(user_id)

    if not facts:
        return ""

    fact_lines = []
    for fact in facts:
        fact_lines.append(f"- {fact['fact_key']}: {fact['fact_value']}")

    return "Known facts about user:\n" + "\n".join(fact_lines)


# ============================================================================
# Cleanup & Maintenance
# ============================================================================

def cleanup_old_sessions(days: int = 30):
    """
    Delete sessions older than specified days.

    Args:
        days: Age threshold in days
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete old conversations
    cursor.execute("""
        DELETE FROM conversations
        WHERE session_id IN (
            SELECT session_id FROM sessions
            WHERE last_activity < ?
        )
    """, (cutoff_date,))

    # Delete old sessions
    cursor.execute("""
        DELETE FROM sessions
        WHERE last_activity < ?
    """, (cutoff_date,))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted_count


def get_session_stats(session_id: str) -> Dict[str, Any]:
    """
    Get statistics for a session.

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with session statistics
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get session info
    cursor.execute("""
        SELECT * FROM sessions WHERE session_id = ?
    """, (session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        return {}

    # Get message count
    cursor.execute("""
        SELECT COUNT(*) as count FROM conversations WHERE session_id = ?
    """, (session_id,))
    message_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "last_activity": session["last_activity"],
        "message_count": message_count,
        "metadata": json.loads(session["metadata"]) if session["metadata"] else {}
    }
