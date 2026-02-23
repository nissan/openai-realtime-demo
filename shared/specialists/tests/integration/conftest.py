"""Integration conftest for specialists — captures both API keys."""
import os
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
