"""
Unit tests for teacher WebSocket router.

Tests POST /escalate and WebSocket /ws/teacher/{session_id}.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.services.human_escalation import _teacher_connections


@pytest.fixture(autouse=True)
def clear_connections():
    """Clear teacher connections between tests."""
    _teacher_connections.clear()
    yield
    _teacher_connections.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_escalate_returns_session_id(client):
    """POST /escalate returns session_id in the response."""
    with patch(
        "backend.routers.teacher.notify_escalation",
        new=AsyncMock(return_value="ws://localhost:8001/ws/teacher/sess-esc"),
    ):
        response = await client.post("/escalate", json={
            "session_id": "sess-esc",
            "reason": "Student requested human help",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-esc"
    assert "teacher_ws_url" in data
    assert "sess-esc" in data["teacher_ws_url"]


@pytest.mark.asyncio
async def test_escalate_calls_notify_escalation(client):
    """POST /escalate invokes the notify_escalation service function."""
    mock_notify = AsyncMock(return_value="ws://test/ws/teacher/sess-x")

    with patch("backend.routers.teacher.notify_escalation", new=mock_notify):
        await client.post("/escalate", json={
            "session_id": "sess-x",
            "reason": "Off-topic content",
            "ws_base_url": "ws://myserver:8001",
        })

    mock_notify.assert_awaited_once_with(
        session_id="sess-x",
        reason="Off-topic content",
        ws_base_url="ws://myserver:8001",
    )


@pytest.mark.asyncio
async def test_escalate_missing_required_fields(client):
    """POST /escalate returns 422 when required fields are missing."""
    response = await client.post("/escalate", json={"reason": "missing session_id"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_websocket_connect():
    """WebSocket /ws/teacher/{session_id} connects, receives greeting, disconnects."""
    pytest.skip("WebSocket testing requires httpx_ws; covered by Playwright E2E tests")


@pytest.mark.asyncio
async def test_escalate_with_custom_ws_base_url(client):
    """POST /escalate respects the optional ws_base_url parameter."""
    mock_notify = AsyncMock(return_value="ws://custom:9000/ws/teacher/sess-c")

    with patch("backend.routers.teacher.notify_escalation", new=mock_notify):
        response = await client.post("/escalate", json={
            "session_id": "sess-c",
            "reason": "test",
            "ws_base_url": "ws://custom:9000",
        })

    assert response.status_code == 200
    assert response.json()["teacher_ws_url"] == "ws://custom:9000/ws/teacher/sess-c"
