"""
WebSocket message types and schemas.

Defines all message types for WebSocket communication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time


class MessageType(str, Enum):
    """WebSocket message types."""
    # Client to server
    CONNECT = "connect"
    CHAT = "chat"
    CANCEL = "cancel"
    PING = "ping"
    AUTHENTICATE = "authenticate"

    # Server to client
    CONNECTED = "connected"
    ERROR = "error"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    PONG = "pong"
    DISCONNECT = "disconnect"


class BaseMessage(BaseModel):
    """Base WebSocket message."""
    type: MessageType
    timestamp: float = Field(default_factory=lambda: time.time())


class ConnectMessage(BaseMessage):
    """Client connection message."""
    type: MessageType = MessageType.CONNECT
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key: str


class AuthenticateMessage(BaseMessage):
    """Authentication message."""
    type: MessageType = MessageType.AUTHENTICATE
    token: str


class ChatMessage(BaseMessage):
    """Chat request message."""
    type: MessageType = MessageType.CHAT
    message_id: str
    prompt: str
    persona: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    use_cache: bool = True
    session_id: Optional[str] = None


class CancelMessage(BaseMessage):
    """Cancel stream message."""
    type: MessageType = MessageType.CANCEL
    message_id: str


class ConnectedMessage(BaseMessage):
    """Server connected confirmation."""
    type: MessageType = MessageType.CONNECTED
    connection_id: str
    server_version: str = "1.0.0"


class StreamStartMessage(BaseMessage):
    """Stream start notification."""
    type: MessageType = MessageType.STREAM_START
    message_id: str
    model: Optional[str] = None
    persona: Optional[str] = None


class StreamChunk(BaseModel):
    """Stream chunk data."""
    delta: str  # New text content
    finish_reason: Optional[str] = None  # "stop", "length", "error"
    tokens_used: int = 0


class StreamChunkMessage(BaseMessage):
    """Stream chunk message."""
    type: MessageType = MessageType.STREAM_CHUNK
    message_id: str
    chunk: StreamChunk


class StreamEndMessage(BaseMessage):
    """Stream end notification."""
    type: MessageType = MessageType.STREAM_END
    message_id: str
    tokens_used: int = 0
    cached: bool = False
    session_id: Optional[str] = None


class StreamErrorMessage(BaseModel):
    """Stream error data."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorMessage(BaseMessage):
    """Error message."""
    type: MessageType = MessageType.ERROR
    message_id: Optional[str] = None
    error: StreamErrorMessage


class PingMessage(BaseMessage):
    """Ping message for keep-alive."""
    type: MessageType = MessageType.PING


class PongMessage(BaseMessage):
    """Pong response."""
    type: MessageType = MessageType.PONG


class DisconnectMessage(BaseMessage):
    """Disconnect notification."""
    type: MessageType = MessageType.DISCONNECT
    reason: Optional[str] = None
    code: int = 1000
