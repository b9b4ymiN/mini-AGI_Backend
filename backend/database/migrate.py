"""
Migration script to migrate from SQLite to PostgreSQL.

Run this script to migrate existing SQLite data to PostgreSQL.

Usage:
    python -m backend.database.migrate
"""

import os
import sys
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

from backend.database.models import Base, Conversation, Session, MemoryFact


# SQLite database path
SQLITE_DB = Path(__file__).parent.parent / "data" / "conversations.db"


async def migrate_sqlite_to_postgres(
    sqlite_path: str,
    postgres_url: str
) -> None:
    """
    Migrate data from SQLite to PostgreSQL.

    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL async connection URL
    """
    print(f"Starting migration from {sqlite_path} to PostgreSQL...")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Create PostgreSQL engine
    print(f"Connecting to PostgreSQL...")
    engine = create_async_engine(postgres_url, echo=True)

    # Create tables
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Migrate sessions
        print("\n--- Migrating sessions ---")
        sqlite_cursor.execute("SELECT * FROM sessions")
        sessions = sqlite_cursor.fetchall()

        for row in sessions:
            session_data = {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                "last_activity": datetime.fromisoformat(row["last_activity"]) if row["last_activity"] else None,
                "message_count": row["message_count"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            }

            db_session = Session(**session_data)
            session.add(db_session)

        await session.commit()
        print(f"Migrated {len(sessions)} sessions")

        # Migrate conversations
        print("\n--- Migrating conversations ---")
        sqlite_cursor.execute("SELECT * FROM conversations")
        conversations = sqlite_cursor.fetchall()

        for row in conversations:
            conv_data = {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "timestamp": datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None,
                "user_message": row["user_message"],
                "ai_response": row["ai_response"],
                "persona": row["persona"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            }

            db_conv = Conversation(**conv_data)
            session.add(db_conv)

        await session.commit()
        print(f"Migrated {len(conversations)} conversations")

        # Migrate memory facts
        print("\n--- Migrating memory facts ---")
        sqlite_cursor.execute("SELECT * FROM memory_facts")
        facts = sqlite_cursor.fetchall()

        for row in facts:
            fact_data = {
                "user_id": row["user_id"],
                "fact_type": row["fact_type"],
                "fact_key": row["fact_key"],
                "fact_value": row["fact_value"],
                "confidence": row["confidence"],
                "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                "updated_at": datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
                "source_session": row["source_session"],
            }

            db_fact = MemoryFact(**fact_data)
            session.add(db_fact)

        await session.commit()
        print(f"Migrated {len(facts)} memory facts")

    # Close connections
    sqlite_conn.close()
    await engine.dispose()

    print("\n=== Migration complete! ===")
    print(f"Sessions: {len(sessions)}")
    print(f"Conversations: {len(conversations)}")
    print(f"Memory facts: {len(facts)}")


async def verify_migration(postgres_url: str) -> None:
    """
    Verify the migration by counting records in PostgreSQL.

    Args:
        postgres_url: PostgreSQL async connection URL
    """
    from sqlalchemy import select, func

    engine = create_async_engine(postgres_url, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Count records
        sessions_count = await session.execute(select(func.count(Session.session_id)))
        conversations_count = await session.execute(select(func.count(Conversation.id)))
        facts_count = await session.execute(select(func.count(MemoryFact.id)))

        print("\n=== Verification ===")
        print(f"Sessions: {sessions_count.scalar()}")
        print(f"Conversations: {conversations_count.scalar()}")
        print(f"Memory facts: {facts_count.scalar()}")

    await engine.dispose()


async def main():
    """Main migration function."""
    # Check if SQLite database exists
    if not SQLITE_DB.exists():
        print(f"Error: SQLite database not found at {SQLITE_DB}")
        print("Make sure the backend has been run at least once to create the database.")
        sys.exit(1)

    # Get PostgreSQL URL from environment
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url or not postgres_url.startswith("postgresql"):
        print("Error: DATABASE_URL environment variable not set or not PostgreSQL")
        print("Set DATABASE_URL in .env file, e.g.:")
        print("DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/backend")
        sys.exit(1)

    print(f"SQLite database: {SQLITE_DB}")
    print(f"PostgreSQL URL: {postgres_url}")

    # Confirm migration
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != "yes":
        print("Migration cancelled.")
        sys.exit(0)

    # Run migration
    await migrate_sqlite_to_postgres(str(SQLITE_DB), postgres_url)

    # Verify migration
    await verify_migration(postgres_url)


if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())
