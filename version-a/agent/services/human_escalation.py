"""Human escalation for Version A: generate LiveKit JWT + notify via Supabase."""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def notify_escalation(
    session_id: str,
    room_name: str,
    reason: str,
) -> Optional[str]:
    """
    Generate a LiveKit teacher JWT and insert escalation event to Supabase.

    Version A difference: teacher gets a LiveKit JWT and joins the room
    with full audio/video capability (not just transcript observation).

    Returns: teacher_token (LiveKit JWT) if successful, None otherwise.
    """
    try:
        from livekit.api import AccessToken, VideoGrants

        api_key = os.environ.get("LIVEKIT_API_KEY", "devkey")
        api_secret = os.environ.get("LIVEKIT_API_SECRET", "secret")

        token = (
            AccessToken(api_key, api_secret)
            .with_identity(f"teacher-{session_id[:8]}")
            .with_name("Teacher")
            .with_grants(VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            ))
            .with_ttl(3600)
            .to_jwt()
        )

        # Save to database
        from version_a.agent.services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO escalation_events
                   (session_id, version, reason, teacher_token)
                   VALUES ($1, 'a', $2, $3)""",
                session_id, reason, token
            )

        logger.info(f"Teacher JWT generated for session {session_id}")
        return token

    except Exception as e:
        logger.error(f"Escalation notification failed: {e}")
        return None
