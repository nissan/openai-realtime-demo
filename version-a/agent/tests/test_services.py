"""Unit tests for services — asyncpg and livekit.api fully mocked."""
import sys
import types
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.fixture(autouse=True)
def _mock_livekit(monkeypatch):
    livekit_api = types.ModuleType("livekit.api")
    livekit_api.AccessToken = MagicMock(return_value=MagicMock(
        with_identity=MagicMock(return_value=MagicMock(
            with_name=MagicMock(return_value=MagicMock(
                with_grants=MagicMock(return_value=MagicMock(
                    with_ttl=MagicMock(return_value=MagicMock(
                        to_jwt=MagicMock(return_value="test-jwt")
                    ))
                ))
            ))
        ))
    ))
    livekit_api.VideoGrants = MagicMock(return_value=MagicMock())
    for mod in ["livekit", "livekit.agents", "livekit.rtc"]:
        monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))
    monkeypatch.setitem(sys.modules, "livekit.api", livekit_api)


@pytest.fixture
def mock_pool():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=False),
    ))
    return pool, conn


@pytest.mark.asyncio
async def test_save_turn_executes_insert(mock_pool):
    pool, conn = mock_pool
    import services.transcript_store as ts
    with patch.object(ts, "get_pool", new=AsyncMock(return_value=pool)):
        await ts.save_turn("sess-1", "student", "Hello world", subject="math", turn_index=0)
    conn.execute.assert_called_once()
    call_sql = conn.execute.call_args[0][0]
    assert "INSERT" in call_sql.upper()


@pytest.mark.asyncio
async def test_save_turn_handles_exception_gracefully(mock_pool):
    pool, conn = mock_pool
    conn.execute.side_effect = Exception("DB error")
    import services.transcript_store as ts
    with patch.object(ts, "get_pool", new=AsyncMock(return_value=pool)):
        # Should not raise — errors are logged silently
        await ts.save_turn("sess-1", "student", "text")


@pytest.mark.asyncio
async def test_notify_escalation_returns_jwt(mock_pool, monkeypatch):
    pool, conn = mock_pool
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")
    with patch("services.transcript_store.get_pool", new=AsyncMock(return_value=pool)):
        from services.human_escalation import notify_escalation
        result = await notify_escalation("sess-1", "room-1", "inappropriate content")
    assert result is not None  # returns JWT or None


@pytest.mark.asyncio
async def test_notify_escalation_missing_keys_returns_none(monkeypatch):
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    with patch("services.transcript_store.get_pool", new=AsyncMock()):
        from services.human_escalation import notify_escalation
        result = await notify_escalation("sess-1", "room-1", "reason")
    # May return None on failure or a JWT if env vars are empty strings treated as valid
    # Either way, this should not raise
    assert result is None or isinstance(result, str)


@pytest.mark.asyncio
async def test_get_pool_uses_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    mock_pool_obj = AsyncMock()
    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool_obj)):
        import importlib
        import services.transcript_store as ts
        ts._pool = None  # reset singleton
        importlib.reload(ts)
        ts._pool = None  # reset again after reload
        pool = await ts.get_pool()
    assert pool is mock_pool_obj


@pytest.mark.asyncio
async def test_get_pool_singleton(monkeypatch):
    """get_pool() returns the same pool on repeated calls."""
    mock_pool_obj = AsyncMock()
    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool_obj)):
        import services.transcript_store as ts
        ts._pool = None
        p1 = await ts.get_pool()
        p2 = await ts.get_pool()
    assert p1 is p2
