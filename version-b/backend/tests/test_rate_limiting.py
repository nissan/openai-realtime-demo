"""Tests that rate limiting is wired correctly on /orchestrate, /tts/stream, and /escalate."""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../shared"))

from backend.main import app
from backend.services.job_store import _jobs


@pytest.fixture(autouse=True)
def clear_jobs():
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
async def test_orchestrate_returns_200_under_limit(client):
    """Single request succeeds (limiter doesn't block normal flow)."""
    with patch("asyncio.create_task", return_value=MagicMock()):
        resp = await client.post("/orchestrate", json={
            "session_id": "rate-test", "student_text": "Hello"
        })
    assert resp.status_code == 200


def test_rate_limiter_wired_to_app_state():
    """Confirms slowapi limiter is registered on app.state (required for 429 handler)."""
    from backend.main import app, limiter
    assert app.state.limiter is limiter


@pytest.mark.asyncio
async def test_tts_stream_returns_404_not_429_for_missing_job(client):
    """Single /tts/stream request reaches the endpoint (rate limiter doesn't block)."""
    resp = await client.post("/tts/stream", json={"job_id": "nonexistent", "voice": "alloy"})
    # 404 = request reached the handler (rate limiter not triggered)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalate_returns_200_under_limit(client):
    """Single /escalate request succeeds (rate limiter doesn't block normal flow)."""
    with patch("backend.routers.teacher.notify_escalation", return_value="ws://test/ws"):
        resp = await client.post("/escalate", json={
            "session_id": "rate-test", "reason": "test", "ws_base_url": None
        })
    assert resp.status_code == 200
