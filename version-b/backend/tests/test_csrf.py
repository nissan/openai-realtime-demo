"""
Unit tests for CSRF protection.

Tests token generation/verification and that protected endpoints reject requests
without a valid CSRF token (using a fixture that removes the conftest override).
"""
import time
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.routers.csrf import make_csrf_token, verify_csrf_token, require_csrf


@pytest.fixture
def real_csrf_check():
    """Remove the conftest CSRF override so endpoints enforce the real check."""
    override = app.dependency_overrides.pop(require_csrf, None)
    yield
    if override is not None:
        app.dependency_overrides[require_csrf] = override


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_csrf_token_returns_token_and_ttl(client):
    """GET /csrf/token returns a token string and ttl=300."""
    response = await client.get("/csrf/token")
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["ttl"] == 300
    # Token must have the expire:sig format
    parts = data["token"].split(":")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert len(parts[1]) == 64  # sha256 hex digest


def test_make_and_verify_token_round_trip():
    """A freshly made token verifies correctly."""
    token = make_csrf_token()
    assert verify_csrf_token(token) is True


def test_expired_token_rejected():
    """A token whose expiry is in the past is rejected."""
    # Build a token that expired 1 second ago
    expire = str(int(time.time()) - 1)
    import hmac, hashlib
    from backend.routers.csrf import CSRF_SECRET
    sig = hmac.new(CSRF_SECRET.encode(), expire.encode(), hashlib.sha256).hexdigest()
    expired_token = f"{expire}:{sig}"
    assert verify_csrf_token(expired_token) is False


@pytest.mark.asyncio
async def test_post_orchestrate_without_csrf_token_returns_403(client, real_csrf_check):
    """POST /orchestrate without X-CSRF-Token header returns 403."""
    response = await client.post("/orchestrate", json={
        "session_id": "sess-csrf-test",
        "student_text": "What is 2+2?",
    })
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_orchestrate_with_valid_csrf_token_accepted(client, real_csrf_check):
    """POST /orchestrate with a valid X-CSRF-Token returns 200."""
    token = make_csrf_token()
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "asyncio.create_task", return_value=MagicMock()
    ):
        response = await client.post(
            "/orchestrate",
            json={"session_id": "sess-csrf-ok", "student_text": "What is 2+2?"},
            headers={"X-CSRF-Token": token},
        )
    assert response.status_code == 200
    assert "job_id" in response.json()
