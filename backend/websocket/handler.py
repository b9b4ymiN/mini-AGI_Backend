"""
WebSocket handler for LLM streaming.

Provides the main WebSocket endpoint and message handling logic.
"""

import asyncio
import json
import uuid
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect, status

from backend.logging_config import get_logger
from backend.orchestrator.personas import get_persona_or_custom
from backend.websocket.connection import ConnectionManager, get_connection_manager, WebSocketConnection
from backend.websocket.messages import (
    BaseMessage,
    CancelMessage,
    ChatMessage,
    ConnectMessage,
    ConnectedMessage,
    DisconnectMessage,
    ErrorMessage,
    MessageType,
    PingMessage,
    PongMessage,
    StreamChunk,
    StreamChunkMessage,
    StreamEndMessage,
    StreamErrorMessage,
    StreamStartMessage,
)

logger = get_logger(__name__)


class WebSocketManager:
    """
    Main WebSocket manager for handling LLM streaming.

    Manages:
    - WebSocket connections
    - Message routing
    - LLM streaming
    - Error handling
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self.connection_manager = get_connection_manager()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """
        Handle a new WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        connection = await self.connection_manager.connect(websocket)

        try:
            # Main message loop
            while True:
                # Receive message
                data = await websocket.receive_text()

                try:
                    message_dict = json.loads(data)
                    await self.handle_message(connection, message_dict)
                except json.JSONDecodeError:
                    await connection.send_json({
                        "type": "error",
                        "error": {
                            "code": "invalid_json",
                            "message": "Invalid JSON format",
                        }
                    })
                except Exception as e:
                    logger.error("message_handling_failed", error=str(e))
                    await connection.send_json({
                        "type": "error",
                        "error": {
                            "code": "message_error",
                            "message": str(e),
                        }
                    })

        except WebSocketDisconnect:
            logger.info("websocket_disconnected", connection_id=connection.connection_id)
        except Exception as e:
            logger.error("websocket_error", connection_id=connection.connection_id, error=str(e))
        finally:
            # Clean up connection
            self.connection_manager.disconnect(connection.connection_id)

    async def handle_message(self, connection: WebSocketConnection, message_dict: Dict) -> None:
        """
        Handle an incoming message.

        Args:
            connection: WebSocket connection
            message_dict: Parsed message dictionary
        """
        message_type = message_dict.get("type")

        if not message_type:
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "missing_type",
                    "message": "Message type is required",
                }
            })
            return

        # Check rate limit
        if not connection.check_rate_limit():
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "rate_limited",
                    "message": "Too many messages. Please slow down.",
                }
            })
            return

        # Route to handler
        if message_type == MessageType.CONNECT:
            await self.handle_connect(connection, message_dict)
        elif message_type == MessageType.CHAT:
            await self.handle_chat(connection, message_dict)
        elif message_type == MessageType.CANCEL:
            await self.handle_cancel(connection, message_dict)
        elif message_type == MessageType.PING:
            await self.handle_ping(connection)
        else:
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "unknown_type",
                    "message": f"Unknown message type: {message_type}",
                }
            })

    async def handle_connect(self, connection: WebSocketConnection, message_dict: Dict) -> None:
        """
        Handle connection message.

        Args:
            connection: WebSocket connection
            message_dict: Message data
        """
        try:
            api_key = message_dict.get("api_key")
            if not api_key:
                await connection.send_json({
                    "type": "error",
                    "error": {
                        "code": "missing_api_key",
                        "message": "API key is required",
                    }
                })
                return

            # Authenticate
            authenticated = await self.connection_manager.authenticate(connection, api_key)

            if not authenticated:
                await connection.send_json({
                    "type": "error",
                    "error": {
                        "code": "authentication_failed",
                        "message": "Invalid API key",
                    }
                })
                await connection.close(code=1008, reason="Authentication failed")
                return

            # Update connection metadata
            connection.session_id = message_dict.get("session_id")
            connection.user_id = message_dict.get("user_id")

            # Send connected confirmation
            await connection.send(ConnectedMessage(
                connection_id=connection.connection_id,
            ))

        except Exception as e:
            logger.error("connect_handler_failed", error=str(e))
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "connect_error",
                    "message": str(e),
                }
            })

    async def handle_chat(self, connection: WebSocketConnection, message_dict: Dict) -> None:
        """
        Handle chat message and start LLM stream.

        Args:
            connection: WebSocket connection
            message_dict: Message data
        """
        if not connection.authenticated:
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "not_authenticated",
                    "message": "Must authenticate first",
                }
            })
            return

        try:
            # Parse chat message
            message_id = message_dict.get("message_id") or str(uuid.uuid4())
            prompt = message_dict.get("prompt")

            if not prompt:
                await connection.send_json({
                    "type": "error",
                    "message_id": message_id,
                    "error": {
                        "code": "missing_prompt",
                        "message": "Prompt is required",
                    }
                })
                return

            persona = message_dict.get("persona")
            model = message_dict.get("model")
            temperature = message_dict.get("temperature")
            max_tokens = message_dict.get("max_tokens")
            use_cache = message_dict.get("use_cache", True)
            session_id = message_dict.get("session_id") or connection.session_id

            # Get system instruction
            system_instruction = get_persona_or_custom(persona, None)

            # Create stream task
            task = asyncio.create_task(
                self.stream_llm_response(
                    connection=connection,
                    message_id=message_id,
                    prompt=prompt,
                    system_instruction=system_instruction,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_cache=use_cache,
                    session_id=session_id,
                )
            )

            # Track active stream
            connection.add_stream(message_id, task)

        except Exception as e:
            logger.error("chat_handler_failed", error=str(e))
            await connection.send_json({
                "type": "error",
                "error": {
                    "code": "chat_error",
                    "message": str(e),
                }
            })

    async def handle_cancel(self, connection: WebSocketConnection, message_dict: Dict) -> None:
        """
        Handle cancel message.

        Args:
            connection: WebSocket connection
            message_dict: Message data
        """
        message_id = message_dict.get("message_id")

        if not message_id:
            return

        # Cancel active stream
        if message_id in connection.active_streams:
            task = connection.active_streams[message_id]
            task.cancel()
            connection.remove_stream(message_id)
            logger.info("stream_cancelled", message_id=message_id, connection_id=connection.connection_id)

    async def handle_ping(self, connection: WebSocketConnection) -> None:
        """Handle ping message."""
        connection.last_ping = connection.connection_id
        await connection.send(PongMessage())
        connection.last_pong = asyncio.get_event_loop().time()

    async def stream_llm_response(
        self,
        connection: WebSocketConnection,
        message_id: str,
        prompt: str,
        system_instruction: str,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        use_cache: bool,
        session_id: Optional[str],
    ) -> None:
        """
        Stream LLM response to client.

        Args:
            connection: WebSocket connection
            message_id: Unique message ID
            prompt: User prompt
            system_instruction: System instruction/persona
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            use_cache: Use response cache
            session_id: Session ID
        """
        try:
            # Send stream start
            await connection.send(StreamStartMessage(
                message_id=message_id,
                model=model,
                persona=None,
            ))

            # Get LLM response (non-streaming for now, can be extended)
            from backend.orchestrator.llm import generate_response
            response_text = await generate_response(
                prompt=prompt,
                system_instruction=system_instruction,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                use_cache=use_cache,
            )

            # Send as chunks (simulate streaming)
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]

                await connection.send(StreamChunkMessage(
                    message_id=message_id,
                    chunk=StreamChunk(delta=chunk),
                ))

                # Small delay to simulate streaming
                await asyncio.sleep(0.01)

            # Send stream end
            await connection.send(StreamEndMessage(
                message_id=message_id,
                tokens_used=len(response_text.split()),  # Approximate
                cached=False,
                session_id=session_id,
            ))

        except asyncio.CancelledError:
            # Stream was cancelled
            await connection.send_json({
                "type": "stream_end",
                "message_id": message_id,
                "cancelled": True,
            })
            logger.info("stream_cancelled", message_id=message_id)

        except Exception as e:
            logger.error("stream_failed", message_id=message_id, error=str(e))
            await connection.send_json({
                "type": "error",
                "message_id": message_id,
                "error": {
                    "code": "stream_error",
                    "message": str(e),
                }
            })

        finally:
            # Remove from active streams
            connection.remove_stream(message_id)


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager


async def websocket_handler(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint handler.

    Args:
        websocket: WebSocket connection
    """
    manager = get_websocket_manager()
    await manager.handle_connection(websocket)
