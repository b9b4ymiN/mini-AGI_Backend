"""
Database module for PostgreSQL with SQLAlchemy.

Provides:
- Async database operations with connection pooling
- SQLAlchemy ORM models
- Support for both PostgreSQL (production) and SQLite (development)
- Database session management
"""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
import logging

logger = logging.getLogger(__name__)

# Database URL configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./backend/data/conversations.db"
)

# Async driver mapping
# SQLite: sqlite+aiosqlite:///
# PostgreSQL: postgresql+asyncpg://user:pass@host:port/db


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Global engine and session maker
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None


def get_engine_config() -> dict:
    """
    Get database engine configuration based on database type.

    Returns:
        Dictionary with engine configuration
    """
    config = {
        "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
        "future": True,
    }

    # Connection pooling configuration
    if DATABASE_URL.startswith("postgresql"):
        # PostgreSQL with connection pooling
        config.update({
            "poolclass": QueuePool,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "pool_pre_ping": True,  # Verify connections before using
        })
    else:
        # SQLite without pooling (single file)
        config.update({
            "poolclass": NullPool,
        })

    return config


async def init_db():
    """
    Initialize the database engine and create tables.

    This should be called on application startup.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.warning("Database already initialized")
        return

    logger.info(f"Initializing database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

    # Create async engine
    config = get_engine_config()
    _engine = create_async_engine(DATABASE_URL, **config)

    # Create session maker
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Import all models to ensure they're registered with Base
    from . import models  # noqa: F401

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def close_db():
    """
    Close the database engine.

    This should be called on application shutdown.
    """
    global _engine, _async_session_maker

    if _engine is None:
        return

    logger.info("Closing database connection...")
    await _engine.dispose()
    _engine = None
    _async_session_maker = None
    logger.info("Database connection closed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for use in dependency injection.

    Yields:
        AsyncSession: Database session

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine() -> Optional[AsyncEngine]:
    """
    Get the current database engine.

    Returns:
        AsyncEngine or None if not initialized
    """
    return _engine


def is_postgresql() -> bool:
    """
    Check if using PostgreSQL database.

    Returns:
        True if using PostgreSQL, False if SQLite
    """
    return DATABASE_URL.startswith("postgresql")


def is_sqlite() -> bool:
    """
    Check if using SQLite database.

    Returns:
        True if using SQLite, False if PostgreSQL
    """
    return DATABASE_URL.startswith("sqlite")
