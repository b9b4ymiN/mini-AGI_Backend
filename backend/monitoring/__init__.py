"""
Monitoring module for distributed tracing and metrics.

Provides OpenTelemetry integration for:
- Distributed tracing with Jaeger/OTLP
- Metrics export to Prometheus
- Request/response tracking
- LLM provider performance tracking
- Response compression
- Webhook notifications
- Alerting system
"""

from .telemetry import (
    init_telemetry,
    shutdown_telemetry,
    get_tracer,
    with_tracing,
    track_llm_request,
    track_cache_hit,
    track_database_query,
)
from .middleware import MonitoringMiddleware
from .compression import CompressionMiddleware
from .webhooks import (
    WebhookEvent,
    Webhook,
    WebhookPayload,
    WebhookManager,
    get_webhook_manager,
    trigger_webhook_event,
)
from .alerts import (
    Alert,
    AlertRule,
    AlertChannel,
    AlertSeverity,
    AlertStatus,
    AlertManager,
    get_alert_manager,
)

__all__ = [
    "init_telemetry",
    "shutdown_telemetry",
    "get_tracer",
    "with_tracing",
    "track_llm_request",
    "track_cache_hit",
    "track_database_query",
    "MonitoringMiddleware",
    "CompressionMiddleware",
    "WebhookEvent",
    "Webhook",
    "WebhookPayload",
    "WebhookManager",
    "get_webhook_manager",
    "trigger_webhook_event",
    "Alert",
    "AlertRule",
    "AlertChannel",
    "AlertSeverity",
    "AlertStatus",
    "AlertManager",
    "get_alert_manager",
]
