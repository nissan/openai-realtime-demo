"""Unit tests for agent module-level constants — no LiveKit runtime needed."""
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


def test_orchestrator_system_prompt_contains_routing_tools():
    from agents.orchestrator import SYSTEM_PROMPT
    assert "math" in SYSTEM_PROMPT.lower()
    assert "history" in SYSTEM_PROMPT.lower()
    assert "english" in SYSTEM_PROMPT.lower()


def test_orchestrator_instructions_match_system_prompt():
    from agents.orchestrator import OrchestratorAgent, SYSTEM_PROMPT
    assert OrchestratorAgent.instructions == SYSTEM_PROMPT


def test_math_agent_system_prompt_set():
    from agents.math_agent import MathAgent, SYSTEM_PROMPT
    assert MathAgent.instructions == SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 20


def test_history_agent_system_prompt_set():
    from agents.history_agent import HistoryAgent, SYSTEM_PROMPT
    assert HistoryAgent.instructions == SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 20


def test_english_agent_system_prompt_set():
    from agents.english_agent import EnglishAgent, SYSTEM_PROMPT
    assert EnglishAgent.instructions == SYSTEM_PROMPT
    assert "english" in SYSTEM_PROMPT.lower() or "writing" in SYSTEM_PROMPT.lower()


def test_orchestrator_has_four_routing_methods():
    from agents.orchestrator import OrchestratorAgent
    for method in ("route_to_math", "route_to_history", "route_to_english", "escalate_to_teacher"):
        assert callable(getattr(OrchestratorAgent, method, None)), f"Missing: {method}"


def test_math_agent_has_back_routing():
    from agents.math_agent import MathAgent
    assert callable(getattr(MathAgent, "route_back_to_orchestrator", None))


def test_history_agent_has_back_routing():
    from agents.history_agent import HistoryAgent
    assert callable(getattr(HistoryAgent, "route_back_to_orchestrator", None))
