"""Transcript store: save turns to Supabase."""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        import asyncpg
        _pool = await asyncpg.create_pool(
            os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
        )
    return _pool


async def save_turn(
    session_id: str,
    speaker: str,
    text: str,
    subject: Optional[str] = None,
    turn_index: int = 0,
) -> None:
    """Save a transcript turn to the database."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO transcript_turns
                   (session_id, speaker, text, subject, turn_index)
                   VALUES ($1, $2, $3, $4, $5)""",
                session_id, speaker, text, subject, turn_index
            )
    except Exception as e:
        logger.error(f"Failed to save transcript turn: {e}")
