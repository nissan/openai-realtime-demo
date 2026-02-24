"""
In-memory job store with background TTL cleanup.
Handles async job lifecycle for orchestration pipeline.
"""
import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# In-memory store: job_id -> OrchestratorJob
_jobs: Dict[str, "OrchestratorJob"] = {}
_cleanup_task: Optional[asyncio.Task] = None


def get_job(job_id: str) -> Optional["OrchestratorJob"]:
    """Retrieve a job by ID."""
    return _jobs.get(job_id)


def store_job(job: "OrchestratorJob") -> None:
    """Store a job in memory."""
    _jobs[job.id] = job
    logger.debug(f"Stored job {job.id}")


def remove_job(job_id: str) -> None:
    """Remove a job from memory."""
    _jobs.pop(job_id, None)


async def cleanup_expired_jobs(ttl_seconds: int = 3600) -> None:
    """Periodically remove old completed jobs to prevent memory growth."""
    from datetime import datetime, timedelta, timezone
    from backend.models.job import JobStatus

    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)

            expired = [
                job_id for job_id, job in _jobs.items()
                if job.status in (JobStatus.COMPLETE, JobStatus.ERROR)
                and job.completed_at
                and job.completed_at < cutoff
            ]

            for job_id in expired:
                remove_job(job_id)

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired jobs")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Job cleanup error: {e}")


def start_cleanup_task() -> asyncio.Task:
    """Start background cleanup task. Call from FastAPI startup."""
    global _cleanup_task
    _cleanup_task = asyncio.create_task(cleanup_expired_jobs())
    return _cleanup_task


def stop_cleanup_task() -> None:
    """Stop cleanup task. Call from FastAPI shutdown."""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None
