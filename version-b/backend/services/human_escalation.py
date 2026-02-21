"""Human escalation for Version B: WebSocket broadcast + Supabase."""
import logging
import os
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

# Active teacher WebSocket connections: session_id -> set of WebSockets
_teacher_connections: Dict[str, Set] = {}


def add_teacher_connection(session_id: str, ws) -> None:
    if session_id not in _teacher_connections:
        _teacher_connections[session_id] = set()
    _teacher_connections[session_id].add(ws)


def remove_teacher_connection(session_id: str, ws) -> None:
    if session_id in _teacher_connections:
        _teacher_connections[session_id].discard(ws)


async def broadcast_to_teachers(session_id: str, message: dict) -> None:
    """Broadcast a message to all teacher observers for a session."""
    connections = _teacher_connections.get(session_id, set())
    disconnected = set()

    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        remove_teacher_connection(session_id, ws)


async def notify_escalation(
    session_id: str,
    reason: str,
    ws_base_url: Optional[str] = None,
) -> Optional[str]:
    """Create escalation event and return teacher WebSocket URL."""
    base_url = ws_base_url or os.environ.get("BACKEND_B_WS_URL", "ws://localhost:8001")
    teacher_ws_url = f"{base_url}/ws/teacher/{session_id}"

    # Broadcast to any already-connected teachers
    await broadcast_to_teachers(session_id, {
        "type": "escalation",
        "session_id": session_id,
        "reason": reason,
        "teacher_ws_url": teacher_ws_url,
    })

    # Save to DB
    try:
        from backend.services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO escalation_events
                   (session_id, version, reason, teacher_ws_url)
                   VALUES ($1, 'b', $2, $3)""",
                session_id, reason, teacher_ws_url
            )
    except Exception as e:
        logger.error(f"Failed to save escalation: {e}")

    return teacher_ws_url
