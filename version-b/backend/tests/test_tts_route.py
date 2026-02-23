"""
Unit tests for TTS streaming router — mocked OpenAI TTS calls.

Tests POST /tts/stream without any network calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.services.job_store import _jobs, store_job
from backend.models.job import OrchestratorJob, JobStatus


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear job store between tests."""
    _jobs.clear()
    yield
    _jobs.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _make_ready_job(safe_text: str = "The answer is 20.") -> OrchestratorJob:
    """Create a completed job ready for TTS."""
    job = OrchestratorJob(session_id="sess-tts", student_text="What is 25% of 80?")
    job.mark_processing("math")
    job.mark_complete(safe_text=safe_text)
    store_job(job)
    return job


@pytest.mark.asyncio
async def test_tts_stream_returns_chunks(client):
    """POST /tts/stream returns StreamingResponse with audio chunks."""
    job = _make_ready_job("The answer is 20.")

    async def fake_audio_chunks(*args, **kwargs):
        yield b"PCM_CHUNK_1"
        yield b"PCM_CHUNK_2"

    mock_response = AsyncMock()
    mock_response.iter_bytes = fake_audio_chunks
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_openai = AsyncMock()
    mock_openai.audio.speech.with_streaming_response.create = MagicMock(
        return_value=mock_response
    )

    with patch("backend.routers.tts.get_openai_client", return_value=mock_openai):
        response = await client.post("/tts/stream", json={
            "job_id": job.id,
            "voice": "alloy",
        })

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/pcm"
    assert "X-Audio-Sample-Rate" in response.headers
    assert response.headers["X-Audio-Sample-Rate"] == "24000"


@pytest.mark.asyncio
async def test_tts_stream_job_not_found(client):
    """POST /tts/stream returns 404 for unknown job_id."""
    response = await client.post("/tts/stream", json={
        "job_id": "nonexistent-job",
        "voice": "alloy",
    })
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tts_stream_job_not_ready(client):
    """POST /tts/stream returns 409 when job is still pending."""
    job = OrchestratorJob(session_id="sess-pending", student_text="hello")
    store_job(job)  # status=PENDING, tts_ready=False

    response = await client.post("/tts/stream", json={
        "job_id": job.id,
        "voice": "alloy",
    })
    assert response.status_code == 409
    assert "not ready" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tts_stream_job_error_state(client):
    """POST /tts/stream returns 422 for a failed job."""
    job = OrchestratorJob(session_id="sess-err", student_text="hello")
    job.mark_error("LLM timeout")
    store_job(job)

    response = await client.post("/tts/stream", json={
        "job_id": job.id,
        "voice": "alloy",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tts_stream_missing_job_id(client):
    """POST /tts/stream returns 422 when job_id field is missing."""
    response = await client.post("/tts/stream", json={"voice": "alloy"})
    assert response.status_code == 422
