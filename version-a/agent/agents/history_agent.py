"""History agent: wraps shared/specialists/history.py in GuardedAgent."""
import logging
from .base import GuardedAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a history tutor. Help students with their history questions.
When you have fully answered the question, use the route_back_to_orchestrator tool."""


class HistoryAgent(GuardedAgent):
    """
    History specialist agent.
    Wraps shared/specialists/history.py answer_history_question in GuardedAgent pipeline.
    CRITICAL: Only exposes route_back_to_orchestrator (no spec-to-spec routing).
    """

    instructions = SYSTEM_PROMPT

    def __init__(self, tts=None, **kwargs):
        super().__init__(**kwargs)
        if tts:
            self._tts = tts

    async def on_enter(self) -> None:
        logger.info("HistoryAgent activated")

    async def route_back_to_orchestrator(self) -> str:
        """Transfer back to orchestrator. Only routing tool available."""
        from .orchestrator import OrchestratorAgent
        userdata = self.session.userdata
        userdata.current_subject = None
        await self.session.transfer_agent(OrchestratorAgent)
        return "Returning to orchestrator"
