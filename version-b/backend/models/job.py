"""OrchestratorJob dataclass for async job tracking."""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
import uuid


class JobStatus(str, Enum):
    """Job status enum with DB constraint mapping."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class OrchestratorJob:
    """
    Tracks an async orchestration job.

    Flow:
    POST /orchestrate -> PENDING (job_id returned immediately, <100ms)
    classifier starts -> PROCESSING
    specialist streams + guardrail runs -> COMPLETE (tts_ready=True)
    client polls GET /orchestrate/{job_id} -> streams POST /tts/stream
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING

    # Input
    student_text: str = ""

    # Classification result
    subject: Optional[str] = None  # 'math'|'history'|'english'

    # Output (set when COMPLETE)
    raw_text: Optional[str] = None      # LLM output before guardrail
    safe_text: Optional[str] = None     # Guardrailed text (use for TTS)
    tts_ready: bool = False             # Client starts streaming when True

    # Error
    error_message: Optional[str] = None

    # Timing
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    classified_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Internal: signals completion to polling clients
    _completion_event: asyncio.Event = field(
        default_factory=asyncio.Event, repr=False
    )

    def mark_processing(self, subject: str) -> None:
        """Mark job as processing after classification."""
        self.status = JobStatus.PROCESSING
        self.subject = subject
        self.classified_at = datetime.now(timezone.utc)

    def mark_complete(self, safe_text: str, raw_text: str = "") -> None:
        """Mark job as complete with guardrailed text."""
        self.status = JobStatus.COMPLETE
        self.safe_text = safe_text
        self.raw_text = raw_text
        self.tts_ready = True
        self.completed_at = datetime.now(timezone.utc)
        self._completion_event.set()

    def mark_error(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.ERROR
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)
        self._completion_event.set()

    async def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """Wait for job to complete. Returns True if completed, False if timeout."""
        try:
            await asyncio.wait_for(self._completion_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
