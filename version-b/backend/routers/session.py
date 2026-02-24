"""Session router: generates OpenAI ephemeral keys for WebRTC."""
import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

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
            model="gpt-4o-realtime-preview-2024-12-17",
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
                "INSERT INTO learning_sessions (session_id, version, started_at) "
                "VALUES ($1, $2, NOW()) "
                "ON CONFLICT (session_id) DO NOTHING",
                session_id, "b",
            )
    except Exception as e:
        logger.warning(f"learning_sessions insert failed: {e}")
