"""
WebSocket support for real-time LLM streaming.

Provides:
- WebSocket endpoint for streaming LLM responses
- Connection management
- Message handling
- Authentication
- Rate limiting per connection
"""

from .handler import websocket_handler, WebSocketManager
from .connection import WebSocketConnection, ConnectionManager
from .messages import WebSocketMessage, MessageType, StreamChunk, StreamEnd, StreamError

__all__ = [
    "websocket_handler",
    "WebSocketManager",
    "WebSocketConnection",
    "ConnectionManager",
    "WebSocketMessage",
    "MessageType",
    "StreamChunk",
    "StreamEnd",
    "StreamError",
]
