"""
Integration tests for version-b orchestrator and session — requires real API keys.

These tests use ASGI transport (no running server needed) but make real calls
to OpenAI and Anthropic APIs. Skipped when keys are absent (see conftest.py).
"""
import pytest
from backend.services.job_store import _jobs


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear job store between tests."""
    _jobs.clear()
    yield
    _jobs.clear()


@pytest.mark.integration
@pytest.mark.timeout(60)
async def test_full_pipeline_math(client):
    """Full pipeline: dispatch → classify (math) → Claude Sonnet → guardrail → complete."""
    post_resp = await client.post("/orchestrate", json={
        "session_id": "integ-math",
        "student_text": "What is 25% of 80?",
    })
    assert post_resp.status_code == 200
    job_id = post_resp.json()["job_id"]

    poll_resp = await client.post(f"/orchestrate/{job_id}/wait", params={"timeout": 45})
    assert poll_resp.status_code == 200
    data = poll_resp.json()
    assert data["status"] == "complete"
    assert data["tts_ready"] is True
    assert "20" in data["safe_text"]


@pytest.mark.integration
@pytest.mark.timeout(60)
async def test_full_pipeline_history(client):
    """Full pipeline: dispatch → classify (history) → GPT-4o → guardrail → complete."""
    post_resp = await client.post("/orchestrate", json={
        "session_id": "integ-history",
        "student_text": "When did World War II end?",
    })
    assert post_resp.status_code == 200
    job_id = post_resp.json()["job_id"]

    poll_resp = await client.post(f"/orchestrate/{job_id}/wait", params={"timeout": 45})
    assert poll_resp.status_code == 200
    data = poll_resp.json()
    assert data["status"] == "complete"
    assert data["subject"] == "history"


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_session_token_real_openai(client):
    """POST /session/token creates a real OpenAI Realtime ephemeral key."""
    response = await client.post("/session/token", params={"session_id": "integ-sess"})
    assert response.status_code == 200
    data = response.json()
    assert "client_secret" in data
    assert data["client_secret"]["value"]  # non-empty
    assert data["session_id"] == "integ-sess"


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_health_with_real_startup(client):
    """Health check passes (baseline — verifies backend started correctly)."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
