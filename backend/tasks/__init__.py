"""
Background task queue for async job processing.

Provides:
- Celery-based task queue
- Long-running LLM task execution
- Batch processing support
- Scheduled task management
- Task result caching
"""

from .celery_app import celery_app, get_celery_app
from .llm_tasks import (
    process_llm_request_task,
    process_batch_llm_task,
    generate_response_task,
    clear_llm_cache_task,
)
from .monitoring_tasks import (
    cleanup_old_logs_task,
    generate_analytics_report_task,
    check_system_health_task,
)

__all__ = [
    "celery_app",
    "get_celery_app",
    "process_llm_request_task",
    "process_batch_llm_task",
    "generate_response_task",
    "clear_llm_cache_task",
    "cleanup_old_logs_task",
    "generate_analytics_report_task",
    "check_system_health_task",
]
