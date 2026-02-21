"""
English agent: uses OpenAI Realtime native session for low-latency voice.

This is the key Version A vs Version B difference:
- Version A: spins up a separate Realtime AgentSession (~230ms TTFB)
- Version B: keeps the Realtime session for everything

TradeoffPanel trigger: English question detected shows this difference.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an English tutor helping students with writing, grammar, and literature.
Provide helpful, encouraging feedback. Use route_back_to_orchestrator when done."""


class EnglishAgent:
    """
    English specialist using OpenAI Realtime native session.
    Separate AgentSession from the main pipeline agents for lower latency.

    Version A: Realtime only used for English (this class).
    Version B: Realtime used for everything.
    """

    instructions = SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def on_enter(self) -> None:
        """Called when session transfers to English agent."""
        logger.info("EnglishAgent (Realtime) activated")

    async def route_back_to_orchestrator(self) -> str:
        """Transfer back to orchestrator. Only routing tool available."""
        from .orchestrator import OrchestratorAgent
        userdata = self.session.userdata
        userdata.current_subject = None
        await self.session.transfer_agent(OrchestratorAgent)
        return "Returning to orchestrator"
