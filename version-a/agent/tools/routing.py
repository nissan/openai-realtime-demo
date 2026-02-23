"""
Routing tools for the orchestrator agent.
CRITICAL: Orchestrator-only routing. No specialist-to-specialist transitions.
Each specialist only has route_back_to_orchestrator, not route_to_other_specialist.
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def _route_to_math_impl(session, question: str) -> str:
    """Route to math specialist. Called by orchestrator @function_tool."""
    from agents.math_agent import MathAgent

    userdata = session.userdata
    userdata.mark_routing()
    userdata.current_subject = "math"

    logger.info(f"Routing to math: {question[:50]}...")
    await session.transfer_agent(MathAgent)
    return f"Routing to math specialist for: {question}"


async def _route_to_history_impl(session, question: str) -> str:
    """Route to history specialist. Called by orchestrator @function_tool."""
    from agents.history_agent import HistoryAgent

    userdata = session.userdata
    userdata.mark_routing()
    userdata.current_subject = "history"

    logger.info(f"Routing to history: {question[:50]}...")
    await session.transfer_agent(HistoryAgent)
    return f"Routing to history specialist for: {question}"


async def _route_to_english_impl(session, question: str) -> str:
    """Route to English (Realtime) specialist. Called by orchestrator @function_tool."""
    from agents.english_agent import EnglishAgent

    userdata = session.userdata
    userdata.mark_routing()
    userdata.current_subject = "english"

    logger.info(f"Routing to English (Realtime): {question[:50]}...")
    await session.transfer_agent(EnglishAgent)
    return f"Routing to English specialist for: {question}"


async def _escalate_impl(session, reason: str) -> str:
    """Escalate to human teacher. Called by orchestrator @function_tool."""
    userdata = session.userdata
    userdata.escalated = True
    userdata.mark_routing()

    logger.warning(f"Escalating session {userdata.session_id}: {reason}")

    try:
        from services.human_escalation import notify_escalation
        await notify_escalation(
            session_id=userdata.session_id,
            room_name=userdata.room_name,
            reason=reason,
        )
    except Exception as e:
        logger.error(f"Escalation notification failed: {e}")

    return f"Escalating to teacher. Reason: {reason}"
