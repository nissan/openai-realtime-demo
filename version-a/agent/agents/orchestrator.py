"""
Orchestrator agent: Claude Haiku, routes to specialists via @function_tool.
CRITICAL: Orchestrator-only routing pattern — never routes specialist-to-specialist.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI tutoring orchestrator. Your role is to:
1. Greet students warmly
2. Understand their question
3. Route them to the appropriate specialist using the available tools
4. NEVER answer subject questions directly — always route to a specialist

Available specialists:
- route_to_math: for any math-related questions
- route_to_history: for history questions
- route_to_english: for writing, grammar, and literature
- escalate_to_teacher: for inappropriate content or complex issues

Always use a routing tool. Briefly acknowledge the question before routing.
Example: "Great question about percentages! Let me connect you with our math specialist."
"""


class OrchestratorAgent:
    """
    Orchestrator agent using Claude Haiku.
    Routes student questions to appropriate specialists via @function_tool.
    CRITICAL: Uses function_tool decorators for routing, never string matching.
    """

    instructions = SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def route_to_math(self, question: str) -> str:
        """Route to math specialist."""
        from version_a.agent.tools.routing import _route_to_math_impl
        return await _route_to_math_impl(self.session, question)

    async def route_to_history(self, question: str) -> str:
        """Route to history specialist."""
        from version_a.agent.tools.routing import _route_to_history_impl
        return await _route_to_history_impl(self.session, question)

    async def route_to_english(self, question: str) -> str:
        """Route to English (Realtime) specialist."""
        from version_a.agent.tools.routing import _route_to_english_impl
        return await _route_to_english_impl(self.session, question)

    async def escalate_to_teacher(self, reason: str) -> str:
        """Escalate to human teacher."""
        from version_a.agent.tools.routing import _escalate_impl
        return await _escalate_impl(self.session, reason)
