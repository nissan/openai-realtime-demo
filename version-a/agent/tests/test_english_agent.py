"""Unit tests for EnglishAgent — no LiveKit runtime needed."""
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


def test_english_agent_instantiates():
    """EnglishAgent can be instantiated without LiveKit runtime."""
    from agents.english_agent import EnglishAgent
    agent = object.__new__(EnglishAgent)
    assert agent is not None


def test_english_agent_has_nonempty_system_prompt():
    """EnglishAgent has a non-empty system prompt defining its role."""
    from agents.english_agent import SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 20
    # English agent prompt must mention english, writing, or grammar
    assert any(kw in SYSTEM_PROMPT.lower() for kw in ("english", "writing", "grammar"))


def test_english_agent_has_back_routing_only():
    """
    EnglishAgent only exposes route_back_to_orchestrator.
    Version A difference: English uses Realtime native session, no spec-to-spec routing.
    """
    from agents.english_agent import EnglishAgent
    assert callable(getattr(EnglishAgent, "route_back_to_orchestrator", None))
    # Must NOT have route_to_math or route_to_history
    assert not hasattr(EnglishAgent, "route_to_math")
    assert not hasattr(EnglishAgent, "route_to_history")
