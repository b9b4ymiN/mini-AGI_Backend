"""
Alerting system for monitoring and notifications.

Provides:
- Threshold-based alerting
- Alert channels (webhook, email, log)
- Alert deduplication
- Alert history
- Alert severity levels
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from backend.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    acknowledged_by: Optional[str] = None


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes default
    last_triggered: float = 0


@dataclass
class AlertChannel:
    """Alert channel configuration."""
    id: str
    name: str
    type: str  # "webhook", "log", "email"
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """
    Central alert management system.

    Features:
    - Rule-based alerting
    - Multiple alert channels
    - Alert deduplication
    - Alert history
    - Alert acknowledgment
    """

    def __init__(self):
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[str, AlertChannel] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._alert_counter = 0
        self._alert_counts: Dict[str, int] = defaultdict(int)

        # Register default channels
        self._register_default_channels()

        # Register default rules
        self._register_default_rules()

    def _register_default_channels(self) -> None:
        """Register default alert channels."""
        # Log channel (always available)
        self.register_channel(AlertChannel(
            id="log",
            name="Log Channel",
            type="log",
            enabled=True,
        ))

    def _register_default_rules(self) -> None:
        """Register default alert rules."""
        # High error rate
        self.register_rule(AlertRule(
            id="high_error_rate",
            name="High Error Rate",
            description="Error rate exceeds 5%",
            metric_name="error_rate",
            condition="gt",
            threshold=0.05,
            severity=AlertSeverity.WARNING,
        ))

        # High response time
        self.register_rule(AlertRule(
            id="high_response_time",
            name="High Response Time",
            description="Average response time exceeds 5 seconds",
            metric_name="avg_response_time_ms",
            condition="gt",
            threshold=5000,
            severity=AlertSeverity.WARNING,
        ))

        # Low cache hit rate
        self.register_rule(AlertRule(
            id="low_cache_hit_rate",
            name="Low Cache Hit Rate",
            description="Cache hit rate below 50%",
            metric_name="cache_hit_rate",
            condition="lt",
            threshold=0.5,
            severity=AlertSeverity.INFO,
        ))

        # Critical error rate
        self.register_rule(AlertRule(
            id="critical_error_rate",
            name="Critical Error Rate",
            description="Error rate exceeds 20%",
            metric_name="error_rate",
            condition="gt",
            threshold=0.2,
            severity=AlertSeverity.CRITICAL,
        ))

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self.rules[rule.id] = rule
        logger.info("alert_rule_registered", rule_id=rule.id, rule_name=rule.name)

    def unregister_rule(self, rule_id: str) -> None:
        """Unregister an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info("alert_rule_unregistered", rule_id=rule_id)

    def register_channel(self, channel: AlertChannel) -> None:
        """Register an alert channel."""
        self.channels[channel.id] = channel
        logger.info("alert_channel_registered", channel_id=channel.id, channel_type=channel.type)

    def unregister_channel(self, channel_id: str) -> None:
        """Unregister an alert channel."""
        if channel_id in self.channels:
            del self.channels[channel_id]
            logger.info("alert_channel_unregistered", channel_id=channel_id)

    def evaluate_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Evaluate a metric against all applicable rules.

        Args:
            metric_name: Name of the metric
            value: Current metric value
            labels: Optional labels for the metric
        """
        current_time = time.time()

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name != metric_name:
                continue

            # Check cooldown
            if current_time - rule.last_triggered < rule.cooldown_seconds:
                continue

            # Evaluate condition
            should_alert = self._evaluate_condition(value, rule.condition, rule.threshold)

            if should_alert:
                self._trigger_alert(rule, value, labels or {})
                rule.last_triggered = current_time

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate if a condition is met."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        return False

    def _trigger_alert(self, rule: AlertRule, value: float, labels: Dict[str, str]) -> None:
        """Trigger an alert."""
        self._alert_counter += 1
        alert_id = f"{rule.id}_{self._alert_counter}"

        alert = Alert(
            id=alert_id,
            title=rule.name,
            description=rule.description,
            severity=rule.severity,
            source=rule.id,
            metric_name=rule.metric_name,
            metric_value=value,
            threshold=rule.threshold,
            labels=labels,
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self._alert_counts[rule.id] += 1

        logger.warning(
            "alert_triggered",
            alert_id=alert_id,
            rule_id=rule.id,
            severity=alert.severity.value,
            metric=rule.metric_name,
            value=value,
            threshold=rule.threshold,
        )

        # Send to channels
        self._send_alert(alert)

    def _send_alert(self, alert: Alert) -> None:
        """Send alert to all enabled channels."""
        for channel in self.channels.values():
            if not channel.enabled:
                continue

            try:
                if channel.type == "log":
                    self._send_log_alert(alert, channel)
                elif channel.type == "webhook":
                    self._send_webhook_alert(alert, channel)
                elif channel.type == "email":
                    self._send_email_alert(alert, channel)
            except Exception as e:
                logger.error("alert_send_failed", channel_id=channel.id, error=str(e))

    def _send_log_alert(self, alert: Alert, channel: AlertChannel) -> None:
        """Send alert to log."""
        log_func = logger.error if alert.severity == AlertSeverity.CRITICAL else logger.warning
        log_func(
            "alert",
            alert_id=alert.id,
            title=alert.title,
            severity=alert.severity.value,
            description=alert.description,
            metric=alert.metric_name,
            value=alert.metric_value,
            threshold=alert.threshold,
        )

    def _send_webhook_alert(self, alert: Alert, channel: AlertChannel) -> None:
        """Send alert to webhook."""
        import requests

        url = channel.config.get("url")
        if not url:
            return

        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "timestamp": alert.timestamp,
            "metric": {
                "name": alert.metric_name,
                "value": alert.metric_value,
                "threshold": alert.threshold,
            },
            "labels": alert.labels,
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_email_alert(self, alert: Alert, channel: AlertChannel) -> None:
        """Send alert via email (placeholder)."""
        # Email sending would be implemented here
        logger.info("email_alert", alert_id=alert.id, to=channel.config.get("to"))

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert identifier
            acknowledged_by: User who acknowledged the alert

        Returns:
            True if alert was acknowledged
        """
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        alert.acknowledged_by = acknowledged_by

        logger.info(
            "alert_acknowledged",
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
        )

        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert identifier

        Returns:
            True if alert was resolved
        """
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()

        # Move from active to history
        del self.active_alerts[alert_id]

        logger.info("alert_resolved", alert_id=alert_id)

        return True

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get all active alerts.

        Args:
            severity: Optional filter by severity

        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def get_alert_history(self, hours: int = 24, limit: int = 100) -> List[Alert]:
        """
        Get alert history.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of alerts to return

        Returns:
            List of historical alerts
        """
        cutoff_time = time.time() - (hours * 3600)

        history = [
            a for a in self.alert_history
            if a.timestamp > cutoff_time
        ]

        return sorted(history, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get a summary of alert status.

        Returns:
            Alert summary statistics
        """
        active_by_severity = defaultdict(int)
        for alert in self.active_alerts.values():
            active_by_severity[alert.severity.value] += 1

        return {
            "active_alerts": len(self.active_alerts),
            "active_by_severity": dict(active_by_severity),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "total_channels": len(self.channels),
            "enabled_channels": sum(1 for c in self.channels.values() if c.enabled),
            "alerts_last_24h": len([a for a in self.alert_history if a.timestamp > time.time() - 86400]),
        }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
