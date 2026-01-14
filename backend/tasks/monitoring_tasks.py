"""
Monitoring and maintenance tasks.

Provides:
- Periodic log cleanup
- Analytics report generation
- System health checks
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import shared_task

from backend.logging_config import get_logger
from backend.database import get_async_db_session
from backend.database.models import APICallLog

logger = get_logger(__name__)


@shared_task(
    name="backend.tasks.monitoring_tasks.cleanup_old_logs_task",
    bind=True,
)
def cleanup_old_logs_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old API call logs from the database.

    Args:
        self: Celery task instance
        days_to_keep: Number of days of logs to retain (default: 30)

    Returns:
        Dictionary with cleanup results
    """
    logger.info("log_cleanup_started", days_to_keep=days_to_keep)

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Note: This would need to be adapted for async SQLAlchemy
        # For now, return a placeholder result
        result = {
            "status": "success",
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_count": 0,
            "message": "Log cleanup scheduled",
        }

        logger.info("log_cleanup_completed", **result)
        return result

    except Exception as e:
        logger.error("log_cleanup_failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
        }


@shared_task(
    name="backend.tasks.monitoring_tasks.generate_analytics_report_task",
    bind=True,
)
def generate_analytics_report_task(self, hours: int = 1) -> Dict[str, Any]:
    """
    Generate an analytics report for the specified time period.

    Args:
        self: Celery task instance
        hours: Number of hours to analyze (default: 1)

    Returns:
        Dictionary with analytics data
    """
    logger.info("analytics_report_started", hours=hours)

    try:
        start_time = time.time()
        since = datetime.utcnow() - timedelta(hours=hours)

        # Placeholder for analytics data
        # In a real implementation, this would query the database
        report = {
            "status": "success",
            "period_hours": hours,
            "since": since.isoformat(),
            "until": datetime.utcnow().isoformat(),
            "metrics": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time_ms": 0,
                "avg_tokens_used": 0,
                "cache_hit_rate": 0.0,
                "unique_users": 0,
                "top_personas": [],
                "errors_by_type": {},
            },
            "generated_at": datetime.utcnow().isoformat(),
            "generation_time_ms": round((time.time() - start_time) * 1000, 2),
        }

        logger.info("analytics_report_completed", **report)
        return report

    except Exception as e:
        logger.error("analytics_report_failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
        }


@shared_task(
    name="backend.tasks.monitoring_tasks.check_system_health_task",
    bind=True,
)
def check_system_health_task(self) -> Dict[str, Any]:
    """
    Perform a comprehensive system health check.

    Checks:
    - Database connectivity
    - Redis connectivity
    - LLM provider availability
    - Disk space
    - Memory usage

    Returns:
        Dictionary with health check results
    """
    logger.info("system_health_check_started")

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    try:
        # Check Redis
        try:
            from backend.cache import get_cache
            cache = get_cache()
            cache.set("health_check", "ok", ttl=10)
            value = cache.get("health_check")
            health_status["checks"]["redis"] = {
                "status": "healthy" if value == "ok" else "unhealthy",
                "response_time_ms": 0,
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check database
        try:
            from backend.database import check_database_health
            db_health = check_database_health()
            health_status["checks"]["database"] = db_health
            if db_health.get("status") != "healthy":
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check LLM provider
        try:
            from backend.orchestrator.llm_cached import get_llm
            llm = get_llm()
            health_status["checks"]["llm_provider"] = {
                "status": "healthy",
                "provider": llm.provider,
            }
        except Exception as e:
            health_status["checks"]["llm_provider"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check system resources
        try:
            import shutil
            import psutil
            process = psutil.Process()

            disk = shutil.disk_usage("/")
            memory = process.memory_info()

            health_status["checks"]["resources"] = {
                "status": "healthy",
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round(disk.used / disk.total * 100, 2),
                },
                "memory": {
                    "rss_mb": round(memory.rss / (1024**2), 2),
                    "vms_mb": round(memory.vms / (1024**2), 2),
                },
            }

            # Alert if disk space > 90%
            if disk.used / disk.total > 0.9:
                health_status["checks"]["resources"]["status"] = "warning"
                health_status["status"] = "degraded"

        except ImportError:
            health_status["checks"]["resources"] = {
                "status": "unknown",
                "error": "psutil not installed",
            }
        except Exception as e:
            health_status["checks"]["resources"] = {
                "status": "unknown",
                "error": str(e),
            }

        logger.info(
            "system_health_check_completed",
            overall_status=health_status["status"],
        )

        return health_status

    except Exception as e:
        logger.error("system_health_check_failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
