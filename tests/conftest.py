"""
Pytest configuration and shared fixtures.

Provides fixtures for:
- Test database (async)
- Test client (FastAPI)
- Mock LLM responses
- Authentication
"""

import os
import sys
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database import init_db, close_db, get_engine, is_sqlite
from backend.database.models import Base, Conversation, Session, MemoryFact
from backend.database.repository import ConversationRepository
from backend.security import verify_api_key, SecurityConfig

# =============================================================================
# Test Configuration
# =============================================================================

# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Override database URL for tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LOG_FORMAT"] = "pretty"  # Use pretty logging in tests
os.environ["LOG_LEVEL"] = "WARNING"  # Reduce noise in tests


# =============================================================================
# Async Event Loop
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests.

    This is needed for pytest-asyncio with Python 3.10+
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """
    Create a test database.

    Uses in-memory SQLite for fast tests.
    """
    from backend.database import _engine, _async_session_maker

    # Save original engine
    original_engine = _engine
    original_session_maker = _async_session_maker

    try:
        # Initialize test database
        await init_db()

        yield

    finally:
        # Close test database
        await close_db()

        # Restore original
        from backend import database
        database._engine = original_engine
        database._async_session_maker = original_session_maker


@pytest_asyncio.fixture
async def db_session(test_db):
    """
    Get a database session for tests.

    The session is automatically rolled back after each test.
    """
    from backend.database import _async_session_maker

    async with _async_session_maker() as session:
        yield session
        # Rollback to keep tests isolated
        await session.rollback()


# =============================================================================
# Repository Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def conversation_repo(db_session):
    """Get a conversation repository instance."""
    return ConversationRepository(db_session)


@pytest_asyncio.fixture
async def test_session(conversation_repo):
    """Create a test session in the database."""
    session_id = await conversation_repo.create_session(user_id="test-user")
    return session_id


@pytest_asyncio.fixture
async def test_conversation(conversation_repo, test_session):
    """Create a test conversation in the database."""
    conv_id = await conversation_repo.save_conversation(
        session_id=test_session,
        user_message="Hello",
        ai_response="Hi there!",
        user_id="test-user",
        persona="test-persona"
    )
    return conv_id


# =============================================================================
# Test Client Fixtures
# =============================================================================

@pytest.fixture
def test_client():
    """
    Get a FastAPI test client.

    Uses synchronous TestClient for simple tests.
    """
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    """
    Get an async HTTP client for testing.

    Use this for async endpoint tests.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# =============================================================================
# Cache Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def reset_cache():
    """
    Reset the global cache between tests.

    Ensures tests use a fresh in-memory cache.
    """
    from backend import cache as cache_module
    # Close existing cache
    await cache_module.close_cache()
    # Force in-memory cache for tests
    with patch.object(cache_module, "REDIS_AVAILABLE", False):
        yield
    # Clean up
    await cache_module.close_cache()


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def test_api_key():
    """Get a valid test API key."""
    return list(SecurityConfig.VALID_API_KEYS)[0] if SecurityConfig.VALID_API_KEYS else "test-key"


@pytest.fixture
def test_admin_key():
    """Get a valid test admin API key."""
    return SecurityConfig.ADMIN_API_KEY


@pytest.fixture
def auth_headers(test_api_key):
    """Get authentication headers for requests."""
    return {"X-API-Key": test_api_key}


@pytest.fixture
def admin_headers(test_admin_key):
    """Get admin authentication headers for requests."""
    return {"X-API-Key": test_admin_key}


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_response():
    """
    Mock LLM response fixture.

    Patches the LLM provider to return predictable responses.
    """
    with patch("backend.orchestrator.llm.call_llm") as mock:
        mock.return_value = "This is a test AI response."
        yield mock


@pytest.fixture
def mock_llm_error():
    """
    Mock LLM error fixture.

    Patches the LLM provider to raise an error.
    """
    with patch("backend.orchestrator.llm.call_llm") as mock:
        from backend.orchestrator.llm import LlmProviderError
        mock.side_effect = LlmProviderError("Test error", "User-friendly error message")
        yield mock


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, how are you?"}]
            }
        ]
    }


@pytest.fixture
def sample_chat_request_with_persona():
    """Sample chat request with persona for testing."""
    return {
        "persona": "test-persona",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, how are you?"}]
            }
        ]
    }


@pytest.fixture
def sample_chat_request_with_system():
    """Sample chat request with system message for testing."""
    return {
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, how are you?"}]
            }
        ]
    }


# =============================================================================
# Orchestration Fixtures
# =============================================================================

@pytest.fixture
def mock_orchestrate():
    """Mock the orchestrate function for testing."""
    with patch("backend.main.orchestrate") as mock:
        mock.return_value = (
            "Test AI response",
            [],
            "test-session-123",
            False
        )
        yield mock


# =============================================================================
# Skip Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may use external services)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (network calls, long operations)"
    )
    config.addinivalue_line(
        "markers", "security: Security-focused tests"
    )
    config.addinivalue_line(
        "markers", "db: Database-related tests"
    )
