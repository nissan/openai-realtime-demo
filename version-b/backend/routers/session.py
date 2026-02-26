"""Session router: generates OpenAI ephemeral keys for WebRTC."""
import json
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

REALTIME_MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")

router = APIRouter(prefix="/session", tags=["session"])
logger = logging.getLogger(__name__)

_openai: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai
    if _openai is None:
        _openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai


class TokenResponse(BaseModel):
    client_secret: dict
    session_id: str


@router.post("/token", response_model=TokenResponse)
async def create_session_token(session_id: str) -> TokenResponse:
    """
    Generate an OpenAI Realtime ephemeral key for a student session.

    The client uses this token to open a WebRTC peer connection directly
    to OpenAI Realtime API — no audio data passes through our backend.

    Version B tradeoff vs Version A (LiveKit):
    - Version A: audio flows through LiveKit media server → full control
    - Version B: audio goes browser→OpenAI directly → lower latency, less infra
    """
    client = get_openai_client()
    try:
        session = await client.beta.realtime.sessions.create(
            model=REALTIME_MODEL,
            voice="alloy",
            instructions=(
                "You are a helpful AI tutor. When a student asks a question, "
                "call dispatch_to_orchestrator with the student's text. "
                "While waiting for the answer, speak a filler phrase like "
                "'Let me think about that...' after 500ms. "
                "Keep responses conversational and encouraging."
            ),
            tools=[
                {
                    "type": "function",
                    "name": "dispatch_to_orchestrator",
                    "description": (
                        "Send the student's question to the backend orchestrator "
                        "which classifies and routes to the correct specialist."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_text": {
                                "type": "string",
                                "description": "The student's question or statement",
                            }
                        },
                        "required": ["student_text"],
                    },
                }
            ],
            tool_choice="auto",
        )

        # Persist learning session (best-effort — don't fail token creation on DB error)
        await _create_learning_session(session_id, token_prefix=session.client_secret.value[:20])

        return TokenResponse(
            client_secret={"value": session.client_secret.value},
            session_id=session_id,
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session token")


async def _create_learning_session(session_id: str, token_prefix: str = "") -> None:
    try:
        from backend.services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO learning_sessions "
                "(session_id, version, session_token, started_at) "
                "VALUES ($1, $2, $3, NOW()) "
                "ON CONFLICT (session_id) DO NOTHING",
                session_id, "b", token_prefix,
            )
    except Exception as e:
        logger.warning(f"learning_sessions insert failed: {e}")


class CloseSessionRequest(BaseModel):
    session_report: dict | None = None


class CloseSessionResponse(BaseModel):
    session_id: str
    closed: bool


@router.post("/{session_id}/close", response_model=CloseSessionResponse)
async def close_session(session_id: str, body: CloseSessionRequest | None = None) -> CloseSessionResponse:
    """
    Mark a session as ended and persist a summary snapshot.

    Accepts an optional session_report dict from the client; if omitted,
    the server builds a minimal report from the audit tables.

    The session_report JSONB column gives operators a self-contained document
    per session without joining transcript_turns, routing_decisions, etc.
    (Architecture Lesson #12: store a session summary snapshot at close time.)
    """
    report = (body.session_report if body else None) or await _build_session_report(session_id)
    await close_session_record(session_id, report)
    return CloseSessionResponse(session_id=session_id, closed=True)


async def close_session_record(session_id: str, session_report: dict) -> None:
    """
    Write ended_at and session_report to learning_sessions.
    Best-effort: never raises (caller must not depend on this succeeding).
    """
    try:
        from backend.services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE learning_sessions "
                "SET ended_at = NOW(), session_report = $2 "
                "WHERE session_id = $1",
                session_id, json.dumps(session_report),
            )
        logger.info(f"Session {session_id} closed with report ({len(session_report)} keys)")
    except Exception as e:
        logger.warning(f"close_session_record failed for {session_id}: {e}")


async def _build_session_report(session_id: str) -> dict:
    """
    Build a minimal session summary from audit tables when the client
    does not provide one.  Returns an empty skeleton on any DB error.
    """
    try:
        from backend.services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            turns = await conn.fetchval(
                "SELECT COUNT(*) FROM transcript_turns WHERE session_id = $1",
                session_id,
            )
            subjects = await conn.fetch(
                "SELECT DISTINCT subject FROM transcript_turns "
                "WHERE session_id = $1 AND subject IS NOT NULL",
                session_id,
            )
            escalated = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM escalation_events WHERE session_id = $1)",
                session_id,
            )
            guardrail_flags = await conn.fetchval(
                "SELECT COUNT(*) FROM guardrail_events WHERE session_id = $1 AND flagged = true",
                session_id,
            )
            routing_rows = await conn.fetch(
                "SELECT to_agent, confidence, transcript_excerpt FROM routing_decisions "
                "WHERE session_id = $1 ORDER BY created_at",
                session_id,
            )
        return {
            "turns": turns or 0,
            "subjects": [r["subject"] for r in subjects],
            "escalated": bool(escalated),
            "guardrail_flags": guardrail_flags or 0,
            "routing_decisions": [
                {
                    "to": r["to_agent"],
                    "confidence": r["confidence"],
                    "excerpt": r["transcript_excerpt"],
                }
                for r in routing_rows
            ],
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning(f"_build_session_report failed for {session_id}: {e}")
        return {"closed_at": datetime.now(timezone.utc).isoformat()}
