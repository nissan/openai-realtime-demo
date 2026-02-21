"""
Unit tests for orchestrator router — mocked LLM calls.

Tests POST /orchestrate and GET /orchestrate/{job_id} without any network.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.services.job_store import _jobs


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


@pytest.mark.asyncio
async def test_dispatch_returns_job_id(client):
    """POST /orchestrate returns job_id immediately (<100ms semantically)."""
    with (
        patch("backend.routers.orchestrator._run_orchestration", new=AsyncMock()),
        patch("asyncio.create_task") as mock_task,
    ):
        mock_task.return_value = MagicMock()
        response = await client.post("/orchestrate", json={
            "session_id": "sess-test",
            "student_text": "What is 25% of 80?",
        })

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_get_job_status_pending(client):
    """GET /orchestrate/{job_id} returns pending status for new job."""
    # First dispatch a job
    with patch("asyncio.create_task", return_value=MagicMock()):
        post_response = await client.post("/orchestrate", json={
            "session_id": "sess-test",
            "student_text": "Hello",
        })
    job_id = post_response.json()["job_id"]

    response = await client.get(f"/orchestrate/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"
    assert data["tts_ready"] is False


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    """GET /orchestrate/nonexistent returns 404."""
    response = await client.get("/orchestrate/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_orchestration_pipeline(client):
    """
    Integration-style test: dispatch job, run background orchestration with
    mocked specialists, verify job completes with safe_text.
    """
    from backend.services.job_store import get_job

    # Mock classifier + specialist + guardrail
    async def mock_classifier(text):
        return "math"

    async def mock_specialist(text):
        yield "The answer is 20."

    async def mock_guardrail(stream):
        async for chunk in stream:
            yield chunk

    with (
        patch("specialists.classifier.route_intent", new=mock_classifier),
        patch("specialists.math.stream_math_response", return_value=mock_specialist("x")),
        patch("guardrail.service.check_stream_with_sentence_buffer", side_effect=mock_guardrail),
        patch("backend.routers.orchestrator._save_transcript", new=AsyncMock()),
    ):
        # Dispatch
        post_resp = await client.post("/orchestrate", json={
            "session_id": "sess-pipeline",
            "student_text": "What is 25% of 80?",
        })
        assert post_resp.status_code == 200
        job_id = post_resp.json()["job_id"]

        # Wait for background task (run it directly for test)
        job = get_job(job_id)
        from backend.routers.orchestrator import _sessions, _run_orchestration
        from backend.models.session_state import SessionUserdata
        session = SessionUserdata(session_id="sess-pipeline")

        await _run_orchestration(job, session)

        # Verify job completed
        assert job.status.value == "complete"
        assert job.tts_ready is True
        assert job.safe_text is not None
        assert len(job.safe_text) > 0


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check returns ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "b"
