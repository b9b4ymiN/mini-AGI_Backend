"""
Database management utilities for monitoring and controlling storage.

Includes:
- Size monitoring
- Automatic cleanup
- Storage limits
- Compression
- Archiving
"""

import sqlite3
import os
import shutil
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from . import memory


# Configuration
MAX_DB_SIZE_MB = 100  # Maximum database size (100 MB for free tier safety)
AUTO_CLEANUP_DAYS = 30  # Auto-cleanup conversations older than this
WARNING_SIZE_MB = 80  # Warning threshold (80% of max)
ARCHIVE_ENABLED = True  # Enable automatic archiving


def get_db_size() -> Dict[str, Any]:
    """
    Get database file size and statistics.

    Returns:
        Dictionary with size info
    """
    db_path = memory.DB_PATH

    if not db_path.exists():
        return {
            "exists": False,
            "size_bytes": 0,
            "size_mb": 0,
            "size_kb": 0
        }

    size_bytes = db_path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024

    return {
        "exists": True,
        "size_bytes": size_bytes,
        "size_kb": round(size_kb, 2),
        "size_mb": round(size_mb, 2),
        "path": str(db_path),
        "max_size_mb": MAX_DB_SIZE_MB,
        "warning_size_mb": WARNING_SIZE_MB,
        "usage_percent": round((size_mb / MAX_DB_SIZE_MB) * 100, 2)
    }


def get_db_stats() -> Dict[str, Any]:
    """
    Get detailed database statistics.

    Returns:
        Dictionary with statistics
    """
    if not memory.DB_PATH.exists():
        return {"error": "Database does not exist"}

    conn = sqlite3.connect(memory.DB_PATH)
    cursor = conn.cursor()

    stats = {}

    # Total conversations
    cursor.execute("SELECT COUNT(*) FROM conversations")
    stats["total_conversations"] = cursor.fetchone()[0]

    # Total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    stats["total_sessions"] = cursor.fetchone()[0]

    # Total facts
    cursor.execute("SELECT COUNT(*) FROM memory_facts")
    stats["total_facts"] = cursor.fetchone()[0]

    # Oldest conversation
    cursor.execute("SELECT MIN(timestamp) FROM conversations")
    oldest = cursor.fetchone()[0]
    stats["oldest_conversation"] = oldest

    # Newest conversation
    cursor.execute("SELECT MAX(timestamp) FROM conversations")
    newest = cursor.fetchone()[0]
    stats["newest_conversation"] = newest

    # Average conversations per session
    if stats["total_sessions"] > 0:
        stats["avg_conversations_per_session"] = round(
            stats["total_conversations"] / stats["total_sessions"], 2
        )
    else:
        stats["avg_conversations_per_session"] = 0

    # Sessions by user
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE user_id IS NOT NULL")
    stats["unique_users"] = cursor.fetchone()[0]

    conn.close()

    # Add size info
    size_info = get_db_size()
    stats.update(size_info)

    return stats


def check_size_limits() -> Dict[str, Any]:
    """
    Check if database is approaching or exceeding size limits.

    Returns:
        Dictionary with status and warnings
    """
    size_info = get_db_size()

    if not size_info["exists"]:
        return {
            "status": "ok",
            "message": "Database does not exist yet"
        }

    size_mb = size_info["size_mb"]
    usage_percent = size_info["usage_percent"]

    if size_mb >= MAX_DB_SIZE_MB:
        return {
            "status": "critical",
            "message": f"Database size ({size_mb} MB) exceeds limit ({MAX_DB_SIZE_MB} MB)!",
            "size_mb": size_mb,
            "limit_mb": MAX_DB_SIZE_MB,
            "usage_percent": usage_percent,
            "action_required": "immediate_cleanup"
        }
    elif size_mb >= WARNING_SIZE_MB:
        return {
            "status": "warning",
            "message": f"Database size ({size_mb} MB) approaching limit ({MAX_DB_SIZE_MB} MB)",
            "size_mb": size_mb,
            "limit_mb": MAX_DB_SIZE_MB,
            "usage_percent": usage_percent,
            "action_required": "schedule_cleanup"
        }
    else:
        return {
            "status": "ok",
            "message": f"Database size ({size_mb} MB) within limits",
            "size_mb": size_mb,
            "limit_mb": MAX_DB_SIZE_MB,
            "usage_percent": usage_percent
        }


def auto_cleanup_if_needed() -> Dict[str, Any]:
    """
    Automatically cleanup old data if approaching size limits.

    Returns:
        Dictionary with cleanup results
    """
    status = check_size_limits()

    if status["status"] == "ok":
        return {
            "cleanup_performed": False,
            "reason": "Size within limits",
            "status": status
        }

    # Perform cleanup
    results = {}

    if status["status"] == "critical":
        # Aggressive cleanup - delete conversations older than 15 days
        deleted = memory.cleanup_old_sessions(days=15)
        results["sessions_deleted"] = deleted
        results["cleanup_days"] = 15
    elif status["status"] == "warning":
        # Normal cleanup - delete conversations older than 30 days
        deleted = memory.cleanup_old_sessions(days=AUTO_CLEANUP_DAYS)
        results["sessions_deleted"] = deleted
        results["cleanup_days"] = AUTO_CLEANUP_DAYS

    # Vacuum database to reclaim space
    vacuum_database()
    results["vacuum_performed"] = True

    # Check size after cleanup
    new_status = check_size_limits()
    results["status_after"] = new_status

    return {
        "cleanup_performed": True,
        "results": results,
        "status_before": status,
        "status_after": new_status
    }


def vacuum_database():
    """
    Vacuum database to reclaim unused space and optimize.
    """
    if not memory.DB_PATH.exists():
        return

    conn = sqlite3.connect(memory.DB_PATH)
    conn.execute("VACUUM")
    conn.close()


def archive_old_conversations(days: int = 90, compress: bool = True) -> Dict[str, Any]:
    """
    Archive old conversations to a separate file and remove from main DB.

    Args:
        days: Archive conversations older than this
        compress: Whether to compress the archive

    Returns:
        Dictionary with archive results
    """
    if not memory.DB_PATH.exists():
        return {"error": "Database does not exist"}

    cutoff_date = datetime.now() - timedelta(days=days)
    archive_date = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create archive filename
    archive_dir = memory.DB_DIR / "archives"
    archive_dir.mkdir(exist_ok=True)

    archive_name = f"conversations_archive_{archive_date}.db"
    if compress:
        archive_name += ".gz"

    archive_path = archive_dir / archive_name

    # Export old conversations
    conn = sqlite3.connect(memory.DB_PATH)
    cursor = conn.cursor()

    # Get old conversations
    cursor.execute("""
        SELECT * FROM conversations
        WHERE timestamp < ?
    """, (cutoff_date,))

    old_conversations = cursor.fetchall()
    count = len(old_conversations)

    if count == 0:
        conn.close()
        return {
            "archived": 0,
            "message": "No conversations to archive"
        }

    # Create archive database
    archive_conn = sqlite3.connect(":memory:")
    archive_cursor = archive_conn.cursor()

    # Create same table structure
    archive_cursor.execute("""
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT,
            timestamp DATETIME,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            persona TEXT,
            metadata TEXT
        )
    """)

    # Insert old conversations
    archive_cursor.executemany("""
        INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, old_conversations)

    archive_conn.commit()

    # Save to file
    if compress:
        # Save compressed
        with gzip.open(archive_path, 'wb') as f:
            for line in archive_conn.iterdump():
                f.write(f"{line}\n".encode('utf-8'))
    else:
        # Save uncompressed
        backup = sqlite3.connect(archive_path)
        archive_conn.backup(backup)
        backup.close()

    archive_conn.close()

    # Delete archived conversations from main database
    cursor.execute("""
        DELETE FROM conversations
        WHERE timestamp < ?
    """, (cutoff_date,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    # Vacuum to reclaim space
    vacuum_database()

    return {
        "archived": count,
        "deleted": deleted,
        "archive_path": str(archive_path),
        "archive_size_kb": round(archive_path.stat().st_size / 1024, 2),
        "cutoff_date": cutoff_date.isoformat()
    }


def optimize_database():
    """
    Optimize database by:
    - Running VACUUM
    - Analyzing tables
    - Rebuilding indexes
    """
    if not memory.DB_PATH.exists():
        return {"error": "Database does not exist"}

    conn = sqlite3.connect(memory.DB_PATH)

    # VACUUM to reclaim space
    conn.execute("VACUUM")

    # ANALYZE to update statistics
    conn.execute("ANALYZE")

    # Reindex
    conn.execute("REINDEX")

    conn.close()

    return {
        "optimized": True,
        "operations": ["VACUUM", "ANALYZE", "REINDEX"]
    }


def get_storage_recommendations() -> Dict[str, Any]:
    """
    Get recommendations for storage management.

    Returns:
        Dictionary with recommendations
    """
    stats = get_db_stats()
    status = check_size_limits()

    recommendations = []

    if status["status"] == "critical":
        recommendations.append({
            "priority": "HIGH",
            "action": "immediate_cleanup",
            "message": "Database exceeds size limit. Run cleanup immediately.",
            "command": "DELETE /sessions/cleanup?days=15"
        })

    elif status["status"] == "warning":
        recommendations.append({
            "priority": "MEDIUM",
            "action": "schedule_cleanup",
            "message": "Database approaching size limit. Schedule cleanup soon.",
            "command": "DELETE /sessions/cleanup?days=30"
        })

    # Check age of oldest conversation
    if stats.get("oldest_conversation"):
        oldest = datetime.fromisoformat(stats["oldest_conversation"])
        age_days = (datetime.now() - oldest).days

        if age_days > 90:
            recommendations.append({
                "priority": "LOW",
                "action": "archive_old_data",
                "message": f"Oldest conversation is {age_days} days old. Consider archiving.",
                "command": "Archive conversations older than 90 days"
            })

    # Check conversation count
    if stats.get("total_conversations", 0) > 10000:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "cleanup_or_archive",
            "message": f"Database has {stats['total_conversations']} conversations. Consider cleanup or archiving.",
            "command": "DELETE /sessions/cleanup?days=30 or archive"
        })

    if not recommendations:
        recommendations.append({
            "priority": "NONE",
            "action": "none",
            "message": "Database is healthy. No action needed."
        })

    return {
        "status": status,
        "stats": stats,
        "recommendations": recommendations
    }
