"""
Orchestrator router for Version B.

POST /orchestrate  → dispatches async job, returns {job_id} in <100ms
GET  /orchestrate/{job_id} → polls job status; streams TTS when complete
"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.job import OrchestratorJob, JobStatus
from backend.models.session_state import SessionUserdata
from backend.services.job_store import get_job, store_job

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])
logger = logging.getLogger(__name__)

# Per-session state: session_id -> SessionUserdata
_sessions: dict[str, SessionUserdata] = {}


class OrchestrationRequest(BaseModel):
    session_id: str
    student_text: str


class OrchestrationResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    subject: str | None = None
    safe_text: str | None = None
    tts_ready: bool = False
    error_message: str | None = None


@router.post("", response_model=OrchestrationResponse)
async def dispatch_orchestration(req: OrchestrationRequest) -> OrchestrationResponse:
    """
    Dispatch an orchestration job. Returns job_id in <100ms.

    CRITICAL: Must NOT await any LLM calls here — fire and forget via
    asyncio.create_task(). The classifier + specialist + guardrail all run
    in the background task.

    Version B tradeoff vs Version A:
    - Version A: LiveKit pipeline handles turn sequencing, barge-in, audio routing
    - Version B: We manage job lifecycle manually with asyncio + polling
    """
    session = _sessions.setdefault(req.session_id, SessionUserdata(session_id=req.session_id))

    job = OrchestratorJob(
        session_id=req.session_id,
        student_text=req.student_text,
    )
    store_job(job)

    # Increment turn counter
    session.turn_count += 1
    session.mark_routing()

    # Fire and forget — NEVER await here
    asyncio.create_task(
        _run_orchestration(job, session),
        name=f"orchestrate-{job.id[:8]}",
    )

    logger.info(f"Dispatched job {job.id} for session {req.session_id}")
    return OrchestrationResponse(job_id=job.id)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Poll job status. Client polls this until tts_ready=True, then calls /tts/stream.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        subject=job.subject,
        safe_text=job.safe_text,
        tts_ready=job.tts_ready,
        error_message=job.error_message,
    )


@router.post("/{job_id}/wait", response_model=JobStatusResponse)
async def wait_for_job(job_id: str, timeout: float = 30.0) -> JobStatusResponse:
    """
    Long-poll endpoint: waits for job completion (up to timeout seconds).
    Client calls this once instead of polling repeatedly.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    completed = await job.wait_for_completion(timeout=timeout)
    if not completed:
        raise HTTPException(status_code=408, detail="Job timed out")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        subject=job.subject,
        safe_text=job.safe_text,
        tts_ready=job.tts_ready,
        error_message=job.error_message,
    )


async def _run_orchestration(job: OrchestratorJob, session: SessionUserdata) -> None:
    """
    Background task: classify → route to specialist → guardrail → mark complete.

    Pipeline:
    1. Classifier (Claude Haiku, temp=0.1) → subject label
    2. Mark job PROCESSING
    3. Specialist streams text (math=Sonnet 4.6, history=GPT-4o, english=GPT-4o)
    4. Sentence-buffered guardrail rewrites harmful content
    5. Accumulated safe text → mark_complete()
    6. Save transcript turn
    """
    try:
        from specialists.classifier import route_intent
        from guardrail.service import check_stream_with_sentence_buffer

        # Step 1: Classify
        subject = await route_intent(job.student_text)
        job.mark_processing(subject)
        session.current_subject = subject
        logger.info(f"Job {job.id[:8]} classified as {subject!r}")

        # Step 2: Get specialist stream
        text_stream = _get_specialist_stream(subject, job.student_text)

        # Step 3: Sentence-buffered guardrail
        safe_chunks: list[str] = []
        raw_chunks: list[str] = []

        async for safe_chunk in check_stream_with_sentence_buffer(text_stream):
            safe_chunks.append(safe_chunk)

        # Also collect raw (re-stream specialist for raw; or store it inline)
        safe_text = "".join(safe_chunks).strip()
        raw_text = safe_text  # Simplified: use safe_text as raw for now

        # Step 4: Mark complete
        job.mark_complete(safe_text=safe_text, raw_text=raw_text)
        session.reset_filler()
        session.consume_skip()

        # Step 5: Persist transcript
        await _save_transcript(job, subject, safe_text)

        logger.info(f"Job {job.id[:8]} complete, {len(safe_text)} chars")

    except Exception as e:
        logger.error(f"Orchestration failed for job {job.id[:8]}: {e}", exc_info=True)
        job.mark_error(str(e))
        session.consume_skip()


def _get_specialist_stream(subject: str, student_text: str):
    """Return async text stream from the appropriate specialist."""
    if subject == "math":
        from specialists.math import stream_math_response
        return stream_math_response(student_text)
    elif subject == "history":
        from specialists.history import stream_history_response
        return stream_history_response(student_text)
    elif subject == "english":
        from specialists.english import stream_english_response
        return stream_english_response(student_text)
    elif subject == "escalate":
        # Return a simple async generator signaling escalation
        async def _escalation_text():
            yield "I'm connecting you with a teacher who can help with this."
        return _escalation_text()
    else:
        # Fallback to english
        from specialists.english import stream_english_response
        return stream_english_response(student_text)


async def _save_transcript(job: OrchestratorJob, subject: str, safe_text: str) -> None:
    try:
        from backend.services.transcript_store import save_turn
        await save_turn(
            session_id=job.session_id,
            speaker=subject,
            text=safe_text,
            subject=subject,
            turn_index=0,
        )
    except Exception as e:
        logger.warning(f"Failed to save transcript for job {job.id[:8]}: {e}")
