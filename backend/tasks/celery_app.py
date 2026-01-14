"""
Celery application configuration for background task processing.

Provides:
- Celery app initialization
- Task configuration
- Result backend setup
- Task routing and prioritization
"""

import os
from typing import Optional

from celery import Celery
from celery.schedules import crontab

from backend.logging_config import get_logger

logger = get_logger(__name__)

# Global Celery app instance
_celery_app: Optional[Celery] = None


def get_celery_app() -> Celery:
    """
    Get or create the global Celery application.

    Returns:
        Configured Celery application instance
    """
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


def create_celery_app() -> Celery:
    """
    Create and configure a Celery application.

    Returns:
        Configured Celery application
    """
    # Get Redis URL for broker and backend
    redis_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # Create Celery app
    celery_app = Celery(
        "mini_agi_tasks",
        broker=redis_url,
        backend=redis_url,
        include=[
            "backend.tasks.llm_tasks",
            "backend.tasks.monitoring_tasks",
        ],
    )

    # Configure Celery
    celery_app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("TZ", "UTC"),
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max per task
        task_soft_time_limit=3000,  # 50 minutes soft limit
        task_acks_late=True,  # Ack only after task completes
        worker_prefetch_multiplier=1,  # Disable prefetch for fair scheduling
        # Result settings
        result_expires=3600,  # Results expire after 1 hour
        result_extended=True,  # Keep results until expired
        # Retry settings
        task_autoretry_for=(Exception,),
        task_retry_kwargs={"max_retries": 3, "countdown": 60},
        # Routing (optional task queues)
        task_default_queue="default",
        task_queues={
            "default": {
                "exchange": "default",
                "routing_key": "default",
            },
            "llm": {
                "exchange": "llm",
                "routing_key": "llm",
            },
            "monitoring": {
                "exchange": "monitoring",
                "routing_key": "monitoring",
            },
        },
        task_default_exchange="default",
        task_default_routing_key="default",
        # Beat scheduler (periodic tasks)
        beat_schedule={
            "cleanup-old-logs-daily": {
                "task": "backend.tasks.monitoring_tasks.cleanup_old_logs_task",
                "schedule": crontab(hour=2, minute=0),  # 2 AM daily
            },
            "generate-analytics-report-hourly": {
                "task": "backend.tasks.monitoring_tasks.generate_analytics_report_task",
                "schedule": crontab(minute=0),  # Every hour
            },
            "check-system-health-every-5-minutes": {
                "task": "backend.tasks.monitoring_tasks.check_system_health_task",
                "schedule": crontab(minute="*/5"),  # Every 5 minutes
            },
        },
    )

    logger.info(
        "celery_app_created",
        broker=redis_url.split("@")[0] + "@***" if "@" in redis_url else redis_url,
        timezone=celery_app.conf.timezone,
    )

    return celery_app


# Create default instance
celery_app = get_celery_app()
