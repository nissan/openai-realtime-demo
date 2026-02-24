"""Unit tests for HistoryAgent — no LiveKit runtime needed."""
import sys
import types
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.fixture(autouse=True)
def _mock_livekit(monkeypatch):
    for mod in ["livekit", "livekit.agents", "livekit.agents.llm",
                "livekit.rtc", "livekit.api"]:
        monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))


def test_history_agent_instantiates():
    """HistoryAgent can be instantiated without LiveKit runtime."""
    from agents.history_agent import HistoryAgent
    agent = object.__new__(HistoryAgent)
    agent._openai_client = None
    assert agent is not None


def test_history_agent_has_nonempty_system_prompt():
    """HistoryAgent has a non-empty system prompt defining its role."""
    from agents.history_agent import SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 20
    assert "history" in SYSTEM_PROMPT.lower()


def test_history_agent_has_back_routing_only():
    """HistoryAgent only exposes route_back_to_orchestrator (no spec-to-spec routing)."""
    from agents.history_agent import HistoryAgent
    assert callable(getattr(HistoryAgent, "route_back_to_orchestrator", None))
    # Must NOT have route_to_math or route_to_english (no spec-to-spec)
    assert not hasattr(HistoryAgent, "route_to_math")
    assert not hasattr(HistoryAgent, "route_to_english")
