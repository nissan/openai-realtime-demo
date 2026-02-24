"""Unit tests for routing tool implementations — all LiveKit calls mocked."""
import json
import sys
import types
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.fixture(autouse=True)
def _mock_livekit(monkeypatch):
    for mod in ["livekit", "livekit.agents", "livekit.agents.llm",
                "livekit.rtc", "livekit.api"]:
        monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))


@pytest.fixture(autouse=True)
def _mock_db(monkeypatch):
    """Prevent asyncpg segfaults by always mocking get_pool in routing tests."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    with patch("services.transcript_store.get_pool", new=AsyncMock(return_value=mock_pool)):
        yield mock_conn


def _make_mock_pool():
    """Return (mock_pool, mock_conn) for asserting DB interactions."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_pool, mock_conn


@pytest.fixture
def session():
    from models.session_state import SessionUserdata
    s = MagicMock()
    s.userdata = SessionUserdata()
    s.transfer_agent = AsyncMock(return_value=None)
    s.room = MagicMock()
    s.room.local_participant = MagicMock()
    s.room.local_participant.publish_data = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_route_to_math_sets_subject(session):
    with patch.dict(sys.modules, {
        "agents.math_agent": MagicMock(MathAgent=MagicMock()),
    }):
        from tools.routing import _route_to_math_impl
        result = await _route_to_math_impl(session, "What is 2+2?")
    assert session.userdata.current_subject == "math"
    assert session.userdata.skip_next_user_turns > 0
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_route_to_history_sets_subject(session):
    with patch.dict(sys.modules, {
        "agents.history_agent": MagicMock(HistoryAgent=MagicMock()),
    }):
        from tools.routing import _route_to_history_impl
        result = await _route_to_history_impl(session, "When did Rome fall?")
    assert session.userdata.current_subject == "history"
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_route_to_english_sets_subject(session):
    with patch.dict(sys.modules, {
        "agents.english_agent": MagicMock(EnglishAgent=MagicMock()),
    }):
        from tools.routing import _route_to_english_impl
        result = await _route_to_english_impl(session, "Fix my grammar.")
    assert session.userdata.current_subject == "english"
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_route_to_math_calls_transfer(session):
    with patch.dict(sys.modules, {
        "agents.math_agent": MagicMock(MathAgent=MagicMock()),
    }):
        from tools.routing import _route_to_math_impl
        await _route_to_math_impl(session, "What is pi?")
    session.transfer_agent.assert_called_once()


@pytest.mark.asyncio
async def test_escalate_sets_escalated_flag(session):
    with patch("services.human_escalation.notify_escalation", new=AsyncMock(return_value="jwt")), \
         patch("services.transcript_store.get_pool", new=AsyncMock()):
        from tools.routing import _escalate_impl
        result = await _escalate_impl(session, "inappropriate content")
    assert session.userdata.escalated is True
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_escalate_increments_skip(session):
    with patch("services.human_escalation.notify_escalation", new=AsyncMock(return_value=None)), \
         patch("services.transcript_store.get_pool", new=AsyncMock()):
        from tools.routing import _escalate_impl
        initial = session.userdata.skip_next_user_turns
        await _escalate_impl(session, "reason")
    assert session.userdata.skip_next_user_turns > initial


@pytest.mark.asyncio
async def test_routing_returns_string_messages(session):
    """All routing functions must return string (used as LLM tool result)."""
    with patch.dict(sys.modules, {
        "agents.math_agent": MagicMock(MathAgent=MagicMock()),
        "agents.history_agent": MagicMock(HistoryAgent=MagicMock()),
        "agents.english_agent": MagicMock(EnglishAgent=MagicMock()),
    }), patch("services.human_escalation.notify_escalation", new=AsyncMock(return_value=None)), \
       patch("services.transcript_store.get_pool", new=AsyncMock()):
        from tools.routing import (
            _route_to_math_impl, _route_to_history_impl,
            _route_to_english_impl, _escalate_impl,
        )
        results = [
            await _route_to_math_impl(session, "q"),
            await _route_to_history_impl(session, "q"),
            await _route_to_english_impl(session, "q"),
            await _escalate_impl(session, "r"),
        ]
    assert all(isinstance(r, str) for r in results)


@pytest.mark.asyncio
async def test_route_to_math_logs_routing_decision(session):
    """Routing to math inserts a routing_decisions row."""
    mock_pool, mock_conn = _make_mock_pool()
    session.userdata.session_id = "test-session-math"
    with patch.dict(sys.modules, {
        "agents.math_agent": MagicMock(MathAgent=MagicMock()),
    }), patch("services.transcript_store.get_pool", new=AsyncMock(return_value=mock_pool)):
        from tools.routing import _route_to_math_impl
        await _route_to_math_impl(session, "What is pi?")
    mock_conn.execute.assert_called()
    sql = mock_conn.execute.call_args[0][0]
    assert "routing_decisions" in sql


@pytest.mark.asyncio
async def test_route_to_math_emits_orchestrator_and_specialist_steps(session):
    """Routing to math emits orchestrator then specialist pipeline steps."""
    with patch.dict(sys.modules, {
        "agents.math_agent": MagicMock(MathAgent=MagicMock()),
    }):
        from tools.routing import _route_to_math_impl
        await _route_to_math_impl(session, "What is 2+2?")
    calls = session.room.local_participant.publish_data.call_args_list
    step_names = [json.loads(c.args[0]).get("step") for c in calls]
    assert "orchestrator" in step_names
    assert "specialist" in step_names


@pytest.mark.asyncio
async def test_escalate_emits_orchestrator_then_clears(session):
    """Escalation emits orchestrator step then clears (no specialist transfer)."""
    with patch("services.human_escalation.notify_escalation", new=AsyncMock(return_value=None)), \
         patch("services.transcript_store.get_pool", new=AsyncMock()):
        from tools.routing import _escalate_impl
        await _escalate_impl(session, "Inappropriate content")
    calls = session.room.local_participant.publish_data.call_args_list
    step_names = [json.loads(c.args[0]).get("step") for c in calls]
    assert "orchestrator" in step_names
    assert None in step_names   # cleared immediately after orchestrator


@pytest.mark.asyncio
async def test_emit_pipeline_step_is_best_effort_on_error(session):
    """publish_data failure does not raise — emit is best-effort."""
    session.room.local_participant.publish_data = AsyncMock(side_effect=Exception("conn error"))
    from tools.routing import _emit_pipeline_step
    # Must not raise even when publish_data fails
    await _emit_pipeline_step(session, "specialist")
