"""
Integration test conftest — real API key capture and singleton reset.
Keys captured at module-load time (before any monkeypatching).
"""
import os
import pytest

_REAL_OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")


@pytest.fixture(autouse=True)
def require_real_api_keys(monkeypatch):
    if not _REAL_OPENAI_KEY or _REAL_OPENAI_KEY.startswith("test-"):
        pytest.skip("OPENAI_API_KEY not configured — skipping integration test")
    monkeypatch.setenv("OPENAI_API_KEY", _REAL_OPENAI_KEY)
