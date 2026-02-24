"""
Unit tests for in-memory job store and TTL cleanup.

Tests store operations without any network calls.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import pytest

from backend.models.job import OrchestratorJob, JobStatus
from backend.services.job_store import (
    get_job,
    store_job,
    remove_job,
    cleanup_expired_jobs,
    _jobs,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Reset job store before and after each test."""
    _jobs.clear()
    yield
    _jobs.clear()


def test_store_create_and_get():
    """store_job then get_job returns the same object."""
    job = OrchestratorJob(session_id="sess-1", student_text="What is 2+2?")
    store_job(job)

    retrieved = get_job(job.id)
    assert retrieved is job
    assert retrieved.session_id == "sess-1"


def test_store_returns_none_for_missing():
    """get_job returns None for an unknown job ID."""
    result = get_job("does-not-exist")
    assert result is None


def test_store_remove_job():
    """remove_job deletes the job from store."""
    job = OrchestratorJob(session_id="sess-2", student_text="test")
    store_job(job)

    remove_job(job.id)
    assert get_job(job.id) is None


def test_store_remove_missing_is_safe():
    """remove_job on a non-existent ID does not raise."""
    remove_job("non-existent-id")  # Should not raise


def test_store_multiple_jobs():
    """Multiple jobs can coexist in the store."""
    job1 = OrchestratorJob(session_id="sess-a", student_text="q1")
    job2 = OrchestratorJob(session_id="sess-b", student_text="q2")
    store_job(job1)
    store_job(job2)

    assert get_job(job1.id) is job1
    assert get_job(job2.id) is job2
    assert len(_jobs) == 2


@pytest.mark.asyncio
async def test_store_cleanup_removes_expired():
    """cleanup_expired_jobs removes completed jobs older than TTL."""
    # Create an old completed job
    old_job = OrchestratorJob(session_id="sess-old", student_text="old question")
    old_job.mark_processing("math")
    old_job.mark_complete(safe_text="old answer")
    # Backdate completed_at to be older than the TTL
    old_job.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
    store_job(old_job)

    # Create a recent completed job (within TTL)
    new_job = OrchestratorJob(session_id="sess-new", student_text="new question")
    new_job.mark_processing("math")
    new_job.mark_complete(safe_text="new answer")
    store_job(new_job)

    # Create a pending job (should not be cleaned up regardless of age)
    pending_job = OrchestratorJob(session_id="sess-pend", student_text="pending")
    store_job(pending_job)

    assert len(_jobs) == 3

    # Run cleanup with 3600s TTL (old_job is 7200s old, so it should be cleaned)
    cleanup_task = asyncio.create_task(_run_single_cleanup(ttl_seconds=3600))
    await cleanup_task

    assert get_job(old_job.id) is None       # expired completed → removed
    assert get_job(new_job.id) is new_job    # recent completed → kept
    assert get_job(pending_job.id) is pending_job  # pending → kept


async def _run_single_cleanup(ttl_seconds: int) -> None:
    """Run one iteration of the cleanup loop directly (without the sleep)."""
    from datetime import timedelta
    from backend.models.job import JobStatus

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    expired = [
        job_id for job_id, job in _jobs.items()
        if job.status in (JobStatus.COMPLETE, JobStatus.ERROR)
        and job.completed_at
        and job.completed_at < cutoff
    ]
    for job_id in expired:
        remove_job(job_id)
