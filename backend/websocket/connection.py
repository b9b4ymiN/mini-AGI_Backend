"""
WebSocket connection management.

Handles connection lifecycle, authentication, and message routing.
"""

import asyncio
import time
import uuid
from typing import Dict, Optional, Set
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

from backend.logging_config import get_logger
from backend.security import verify_api_key_ws
from backend.websocket.messages import (
    BaseMessage,
    ConnectedMessage,
    DisconnectMessage,
    ErrorMessage,
    MessageType,
    StreamErrorMessage,
)

logger = get_logger(__name__)


class WebSocketConnection:
    """
    Represents a single WebSocket connection.

    Manages:
    - Connection state
    - Authentication
    - Rate limiting
    - Active streams
    """

    def __init__(self, websocket: WebSocket, connection_id: str):
        """Initialize connection."""
        self.websocket = websocket
        self.connection_id = connection_id
        self.connected_at = time.time()
        self.last_ping = time.time()
        self.last_pong = time.time()

        # Authentication state
        self.authenticated = False
        self.api_key_hash: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None

        # Active streams (message_id -> task)
        self.active_streams: Dict[str, asyncio.Task] = {}

        # Message count for rate limiting
        self.message_count = 0
        self.messages_per_minute = 0
        self.last_minute_reset = time.time()

    async def send(self, message: BaseMessage) -> None:
        """
        Send a message to this connection.

        Args:
            message: Message to send
        """
        try:
            await self.websocket.send_json(message.model_dump())
        except Exception as e:
            logger.error(
                "websocket_send_failed",
                connection_id=self.connection_id,
                error=str(e),
            )
            raise

    async def send_json(self, data: dict) -> None:
        """
        Send raw JSON data.

        Args:
            data: JSON data to send
        """
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(
                "websocket_send_failed",
                connection_id=self.connection_id,
                error=str(e),
            )
            raise

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Close the connection.

        Args:
            code: WebSocket close code
            reason: Close reason
        """
        # Cancel all active streams
        for message_id, task in self.active_streams.items():
            if not task.done():
                task.cancel()
                logger.info("stream_cancelled", message_id=message_id, connection_id=self.connection_id)

        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception:
            pass  # Connection may already be closed

    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """
        Check if connection has expired.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            True if connection is expired
        """
        return (time.time() - self.last_pong) > timeout_seconds

    def check_rate_limit(self, max_per_minute: int = 60) -> bool:
        """
        Check if connection is rate limited.

        Args:
            max_per_minute: Maximum messages per minute

        Returns:
            True if within rate limit
        """
        now = time.time()

        # Reset counter every minute
        if now - self.last_minute_reset > 60:
            self.messages_per_minute = 0
            self.last_minute_reset = now

        self.messages_per_minute += 1
        return self.messages_per_minute <= max_per_minute

    def add_stream(self, message_id: str, task: asyncio.Task) -> None:
        """Add an active stream."""
        self.active_streams[message_id] = task

    def remove_stream(self, message_id: str) -> None:
        """Remove an active stream."""
        self.active_streams.pop(message_id, None)


class ConnectionManager:
    """
    Manages all WebSocket connections.

    Features:
    - Connection tracking
    - Broadcasting
    - Authentication
    - Cleanup of stale connections
    """

    def __init__(self):
        """Initialize connection manager."""
        # All active connections
        self.connections: Dict[str, WebSocketConnection] = {}

        # User ID to connection IDs mapping
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)

        # Session ID to connection IDs mapping
        self.session_connections: Dict[str, Set[str]] = defaultdict(set)

        # Background task for cleanup
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> WebSocketConnection:
        """
        Accept and register a new connection.

        Args:
            websocket: WebSocket connection

        Returns:
            WebSocketConnection instance
        """
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(websocket, connection_id)
        self.connections[connection_id] = connection

        logger.info("websocket_connected", connection_id=connection_id)

        return connection

    async def authenticate(
        self,
        connection: WebSocketConnection,
        api_key: str
    ) -> bool:
        """
        Authenticate a connection.

        Args:
            connection: Connection to authenticate
            api_key: API key for authentication

        Returns:
            True if authenticated
        """
        try:
            # Verify API key
            auth_result = await verify_api_key_ws(api_key)

            connection.authenticated = True
            connection.api_key_hash = auth_result.get("api_key_hash")
            connection.user_id = auth_result.get("user_id")
            connection.session_id = auth_result.get("session_id")

            # Update mappings
            if connection.user_id:
                self.user_connections[connection.user_id].add(connection.connection_id)
            if connection.session_id:
                self.session_connections[connection.session_id].add(connection.connection_id)

            logger.info(
                "websocket_authenticated",
                connection_id=connection.connection_id,
                user_id=connection.user_id,
            )

            return True

        except Exception as e:
            logger.warning(
                "websocket_auth_failed",
                connection_id=connection.connection_id,
                error=str(e),
            )
            return False

    def disconnect(self, connection_id: str) -> None:
        """
        Remove a connection.

        Args:
            connection_id: Connection ID to remove
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]

        # Remove from mappings
        if connection.user_id:
            self.user_connections[connection.user_id].discard(connection_id)
        if connection.session_id:
            self.session_connections[connection.session_id].discard(connection_id)

        # Remove connection
        del self.connections[connection_id]

        logger.info("websocket_disconnected", connection_id=connection_id)

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Get a connection by ID.

        Args:
            connection_id: Connection ID

        Returns:
            Connection or None
        """
        return self.connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> Set[WebSocketConnection]:
        """
        Get all connections for a user.

        Args:
            user_id: User ID

        Returns:
            Set of connections
        """
        connection_ids = self.user_connections.get(user_id, set())
        return {
            self.connections[cid]
            for cid in connection_ids
            if cid in self.connections
        }

    def get_session_connections(self, session_id: str) -> Set[WebSocketConnection]:
        """
        Get all connections for a session.

        Args:
            session_id: Session ID

        Returns:
            Set of connections
        """
        connection_ids = self.session_connections.get(session_id, set())
        return {
            self.connections[cid]
            for cid in connection_ids
            if cid in self.connections
        }

    async def broadcast_to_user(self, user_id: str, message: BaseMessage) -> int:
        """
        Broadcast a message to all connections for a user.

        Args:
            user_id: User ID
            message: Message to broadcast

        Returns:
            Number of connections sent to
        """
        connections = self.get_user_connections(user_id)
        count = 0

        for connection in list(connections):
            try:
                await connection.send(message)
                count += 1
            except Exception:
                # Remove failed connection
                self.disconnect(connection.connection_id)

        return count

    async def broadcast_to_session(self, session_id: str, message: BaseMessage) -> int:
        """
        Broadcast a message to all connections for a session.

        Args:
            session_id: Session ID
            message: Message to broadcast

        Returns:
            Number of connections sent to
        """
        connections = self.get_session_connections(session_id)
        count = 0

        for connection in list(connections):
            try:
                await connection.send(message)
                count += 1
            except Exception:
                # Remove failed connection
                self.disconnect(connection.connection_id)

        return count

    async def cleanup_stale(self, timeout_seconds: int = 3600) -> int:
        """
        Remove stale connections.

        Args:
            timeout_seconds: Timeout before connection is stale

        Returns:
            Number of connections removed
        """
        stale_connections = [
            cid for cid, conn in self.connections.items()
            if conn.is_expired(timeout_seconds)
        ]

        for cid in stale_connections:
            connection = self.connections[cid]
            await connection.close(code=1000, reason="Stale connection")
            self.disconnect(cid)

        if stale_connections:
            logger.info("websocket_cleanup", count=len(stale_connections))

        return len(stale_connections)

    def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """
        Start background cleanup task.

        Args:
            interval_seconds: Cleanup interval
        """
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_stale()
                except Exception as e:
                    logger.error("websocket_cleanup_failed", error=str(e))
                await asyncio.sleep(interval_seconds)

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("websocket_cleanup_started", interval=interval_seconds)

    def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None


# Global connection manager
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
