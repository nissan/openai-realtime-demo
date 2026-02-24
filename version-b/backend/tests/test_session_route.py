"""
Unit tests for session router — mocked OpenAI ephemeral key calls.

Tests POST /session/token without any network calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _make_session_response(secret_value: str = "ephemeral-key-xyz"):
    """Create a mock OpenAI Realtime session response."""
    mock_session = MagicMock()
    mock_session.client_secret = MagicMock()
    mock_session.client_secret.value = secret_value
    return mock_session


@pytest.mark.asyncio
async def test_session_token_endpoint(client):
    """POST /session/token returns client_secret and session_id."""
    mock_openai = AsyncMock()
    mock_openai.beta.realtime.sessions.create = AsyncMock(
        return_value=_make_session_response("ek-test-token-123")
    )

    with (
        patch("backend.routers.session.get_openai_client", return_value=mock_openai),
        patch("backend.routers.session._create_learning_session", new=AsyncMock()),
    ):
        response = await client.post(
            "/session/token",
            params={"session_id": "sess-abc123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "client_secret" in data
    assert data["client_secret"]["value"] == "ek-test-token-123"
    assert data["session_id"] == "sess-abc123"


@pytest.mark.asyncio
async def test_session_token_returns_provided_session_id(client):
    """POST /session/token echoes back the caller-provided session_id."""
    mock_openai = AsyncMock()
    mock_openai.beta.realtime.sessions.create = AsyncMock(
        return_value=_make_session_response()
    )

    with (
        patch("backend.routers.session.get_openai_client", return_value=mock_openai),
        patch("backend.routers.session._create_learning_session", new=AsyncMock()),
    ):
        response = await client.post(
            "/session/token",
            params={"session_id": "student-session-xyz"},
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "student-session-xyz"


@pytest.mark.asyncio
async def test_session_token_openai_error(client):
    """POST /session/token returns 500 when OpenAI API fails."""
    mock_openai = AsyncMock()
    mock_openai.beta.realtime.sessions.create = AsyncMock(
        side_effect=Exception("OpenAI API unavailable")
    )

    with patch("backend.routers.session.get_openai_client", return_value=mock_openai):
        response = await client.post(
            "/session/token",
            params={"session_id": "sess-fail"},
        )

    assert response.status_code == 500
    assert "Failed to create session token" in response.json()["detail"]
