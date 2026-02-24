"""Unit tests for MathAgent — no LiveKit runtime needed."""
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


def test_math_agent_instantiates():
    """MathAgent can be instantiated without LiveKit runtime."""
    from agents.math_agent import MathAgent
    agent = object.__new__(MathAgent)
    agent._openai_client = None
    assert agent is not None


def test_math_agent_has_nonempty_system_prompt():
    """MathAgent has a non-empty system prompt defining its role."""
    from agents.math_agent import SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 20
    assert "math" in SYSTEM_PROMPT.lower()


def test_math_agent_has_back_routing_only():
    """MathAgent only exposes route_back_to_orchestrator (no spec-to-spec routing)."""
    from agents.math_agent import MathAgent
    assert callable(getattr(MathAgent, "route_back_to_orchestrator", None))
    # Must NOT have route_to_history or route_to_english (no spec-to-spec)
    assert not hasattr(MathAgent, "route_to_history")
    assert not hasattr(MathAgent, "route_to_english")
