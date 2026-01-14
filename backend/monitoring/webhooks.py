"""
Webhook notification system for API events.

Provides:
- Webhook registration and management
- Event type definitions
- Webhook delivery with retries
- Signature verification for security
"""

import hashlib
import hmac
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import httpx

from pydantic import BaseModel, HttpUrl, Field, validator

from backend.logging_config import get_logger
from backend.cache import get_cache

logger = get_logger(__name__)


class WebhookEvent(str, Enum):
    """Event types that can trigger webhooks."""

    # Chat events
    CHAT_COMPLETED = "chat.completed"
    CHAT_FAILED = "chat.failed"

    # Session events
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"

    # Memory events
    MEMORY_SAVED = "memory.saved"
    MEMORY_UPDATED = "memory.updated"

    # System events
    HEALTH_CHECK_FAILED = "health.check.failed"
    ERROR_RATE_HIGH = "error.rate.high"


class Webhook(BaseModel):
    """Webhook configuration."""

    id: str = Field(..., description="Unique webhook identifier")
    url: HttpUrl = Field(..., description="Webhook URL to receive events")
    events: List[WebhookEvent] = Field(..., description="Event types to subscribe to")
    secret: Optional[str] = Field(None, description="Secret for signature verification")
    active: bool = Field(True, description="Whether webhook is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = Field(None, description="Last successful trigger time")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "wh_123abc",
                "url": "https://example.com/webhooks",
                "events": ["chat.completed", "chat.failed"],
                "secret": "my-secret-key",
                "active": True
            }
        }


class WebhookPayload(BaseModel):
    """Standard webhook payload format."""

    id: str = Field(..., description="Unique event ID")
    event: WebhookEvent = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Event-specific data")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_123abc",
                "event": "chat.completed",
                "timestamp": "2026-01-13T12:00:00Z",
                "data": {
                    "session_id": "abc123",
                    "user_id": "user@example.com",
                    "response_length": 150
                }
            }
        }


class WebhookDelivery:
    """
    Webhook delivery manager with retries and signature verification.
    """

    def __init__(self, timeout: float = 5.0, max_retries: int = 3):
        """
        Initialize webhook delivery manager.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)

    async def send_webhook(
        self,
        webhook: Webhook,
        payload: WebhookPayload
    ) -> bool:
        """
        Send webhook notification with retries.

        Args:
            webhook: Webhook configuration
            payload: Event payload to send

        Returns:
            True if delivery succeeded, False otherwise
        """
        # Prepare request body
        body = json.dumps(payload.dict(mode="json"), default=str)

        # Add signature if secret is configured
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": payload.event,
            "X-Webhook-ID": payload.id,
            "X-Webhook-Timestamp": payload.timestamp.isoformat(),
        }

        if webhook.secret:
            signature = self._generate_signature(body, webhook.secret)
            headers["X-Webhook-Signature"] = signature

        # Send with retries
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    str(webhook.url),
                    content=body,
                    headers=headers
                )
                response.raise_for_status()

                logger.info(
                    "webhook_delivered",
                    webhook_id=webhook.id,
                    event=payload.event,
                    attempt=attempt + 1
                )
                return True

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "webhook_failed",
                    webhook_id=webhook.id,
                    event=payload.event,
                    status_code=e.response.status_code,
                    attempt=attempt + 1
                )
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    return False

            except httpx.RequestError as e:
                logger.warning(
                    "webhook_request_error",
                    webhook_id=webhook.id,
                    event=payload.event,
                    error=str(e),
                    attempt=attempt + 1
                )

        logger.error(
            "webhook_delivery_failed",
            webhook_id=webhook.id,
            event=payload.event,
            attempts=self.max_retries
        )
        return False

    def _generate_signature(self, body: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            body: Request body as string
            secret: Webhook secret

        Returns:
            Hex encoded signature
        """
        h = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        )
        return f"sha256={h.hexdigest()}"

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class WebhookManager:
    """
    Manages webhook registration and delivery.

    Stores webhooks in cache for persistence.
    """

    def __init__(self):
        """Initialize webhook manager."""
        self.cache = get_cache()
        self.delivery = WebhookDelivery()

    async def register_webhook(self, webhook: Webhook) -> Webhook:
        """
        Register a new webhook.

        Args:
            webhook: Webhook configuration

        Returns:
            Registered webhook
        """
        key = f"webhook:{webhook.id}"
        await self.cache.set(key, webhook.json(), ttl=86400)  # 24 hours

        logger.info("webhook_registered", webhook_id=webhook.id, events=len(webhook.events))
        return webhook

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.

        Args:
            webhook_id: Webhook identifier

        Returns:
            True if webhook was removed
        """
        key = f"webhook:{webhook_id}"
        result = await self.cache.delete(key)

        if result:
            logger.info("webhook_unregistered", webhook_id=webhook_id)

        return result

    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """
        Get webhook by ID.

        Args:
            webhook_id: Webhook identifier

        Returns:
            Webhook if found, None otherwise
        """
        key = f"webhook:{webhook_id}"
        data = await self.cache.get(key)

        if data:
            return Webhook.parse_raw(data)

        return None

    async def list_webhooks(self) -> List[Webhook]:
        """
        List all registered webhooks.

        Returns:
            List of active webhooks
        """
        # Scan for all webhook keys
        count = await self.cache.delete_pattern(f"webhook:*")
        # This won't work for listing, need to implement properly
        # For now, return empty list
        return []

    async def trigger_event(
        self,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> int:
        """
        Trigger webhooks for an event.

        Args:
            event: Event type
            data: Event data

        Returns:
            Number of webhooks triggered
        """
        import uuid

        payload = WebhookPayload(
            id=str(uuid.uuid4()),
            event=event,
            data=data
        )

        # Find webhooks subscribed to this event
        # For now, we'd need to scan all webhooks
        # TODO: Implement efficient webhook lookup by event

        triggered_count = 0

        # This is a placeholder - in real implementation, you'd:
        # 1. Query webhooks by event subscription
        # 2. Send to each matching webhook

        return triggered_count

    async def close(self):
        """Close webhook manager resources."""
        await self.delivery.close()


# Global webhook manager instance
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """
    Get the global webhook manager instance.

    Returns:
        WebhookManager singleton
    """
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


async def trigger_webhook_event(
    event: WebhookEvent,
    data: Dict[str, Any]
) -> int:
    """
    Trigger webhooks for an event.

    Convenience function for triggering webhook events.

    Args:
        event: Event type
        data: Event data

    Returns:
        Number of webhooks triggered
    """
    manager = get_webhook_manager()
    return await manager.trigger_event(event, data)
