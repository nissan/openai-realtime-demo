"""Unit tests for OrchestratorJob model — no network calls."""
import asyncio
import pytest
from datetime import datetime

from backend.models.job import OrchestratorJob, JobStatus


def test_job_initial_state():
    job = OrchestratorJob(session_id="sess-1", student_text="What is 2+2?")
    assert job.status == JobStatus.PENDING
    assert job.tts_ready is False
    assert job.safe_text is None
    assert job.session_id == "sess-1"
    assert job.student_text == "What is 2+2?"
    assert job.id  # uuid generated


def test_mark_processing():
    job = OrchestratorJob()
    job.mark_processing("math")
    assert job.status == JobStatus.PROCESSING
    assert job.subject == "math"
    assert isinstance(job.classified_at, datetime)


def test_mark_complete():
    job = OrchestratorJob()
    job.mark_processing("math")
    job.mark_complete(safe_text="4", raw_text="The answer is 4.")
    assert job.status == JobStatus.COMPLETE
    assert job.tts_ready is True
    assert job.safe_text == "4"
    assert job.raw_text == "The answer is 4."
    assert isinstance(job.completed_at, datetime)


def test_mark_error():
    job = OrchestratorJob()
    job.mark_error("LLM timeout")
    assert job.status == JobStatus.ERROR
    assert job.error_message == "LLM timeout"
    assert job.tts_ready is False
    assert isinstance(job.completed_at, datetime)


def test_job_status_enum_values():
    """Ensure status values match DB CHECK constraint."""
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.PROCESSING.value == "processing"
    assert JobStatus.COMPLETE.value == "complete"
    assert JobStatus.ERROR.value == "error"


@pytest.mark.asyncio
async def test_wait_for_completion_success():
    """wait_for_completion returns True when job completes."""
    job = OrchestratorJob()

    async def complete_later():
        await asyncio.sleep(0.05)
        job.mark_complete(safe_text="done")

    asyncio.create_task(complete_later())
    result = await job.wait_for_completion(timeout=2.0)
    assert result is True
    assert job.tts_ready is True


@pytest.mark.asyncio
async def test_wait_for_completion_timeout():
    """wait_for_completion returns False on timeout."""
    job = OrchestratorJob()
    # Never complete the job
    result = await job.wait_for_completion(timeout=0.05)
    assert result is False
    assert job.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_completion_event_set_on_error():
    """mark_error also sets completion event (so wait_for_completion unblocks)."""
    job = OrchestratorJob()

    async def error_later():
        await asyncio.sleep(0.05)
        job.mark_error("something went wrong")

    asyncio.create_task(error_later())
    result = await job.wait_for_completion(timeout=2.0)
    assert result is True
    assert job.status == JobStatus.ERROR
