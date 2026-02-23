"""Integration conftest for version-b — captures both API keys."""
import os
import sys
import pytest

_REAL_OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
_REAL_ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


@pytest.fixture(autouse=True)
def require_real_api_keys(monkeypatch):
    if not _REAL_OPENAI_KEY or _REAL_OPENAI_KEY.startswith("test-"):
        pytest.skip("OPENAI_API_KEY not configured — skipping integration test")
    if not _REAL_ANTHROPIC_KEY or _REAL_ANTHROPIC_KEY.startswith("test-"):
        pytest.skip("ANTHROPIC_API_KEY not configured — skipping integration test")
    monkeypatch.setenv("OPENAI_API_KEY", _REAL_OPENAI_KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _REAL_ANTHROPIC_KEY)
    # Reset lazy singleton in session router so it picks up the real key
    import backend.routers.session as session_router
    session_router._openai = None


@pytest.fixture
async def client():
    """ASGI test client wired to the real FastAPI app."""
    # Add shared/ to sys.path so specialists/guardrail are importable
    shared_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../shared")
    )
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

    from httpx import AsyncClient, ASGITransport
    from backend.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
