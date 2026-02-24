"""
Teacher WebSocket router for Version B.

WebSocket /ws/teacher/{session_id}
  - Teacher connects to observe a student session in real time
  - Receives all transcript turns + escalation events
  - Can inject text that appears as 'teacher hint' in student session

Version B tradeoff vs Version A (LiveKit):
- Version A: Teacher joins a LiveKit room → full audio/video, media routing,
  guaranteed delivery via WebRTC data channels
- Version B: Teacher observes via WebSocket → transcript + text injection only,
  simpler infra but no audio/video for teacher

Also handles: POST /ws/teacher/notify → triggers escalation notification
"""
import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.routers.csrf import require_csrf

from backend.services.human_escalation import (
    add_teacher_connection,
    remove_teacher_connection,
    notify_escalation,
    broadcast_to_teachers,
)

router = APIRouter(tags=["teacher"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.websocket("/ws/teacher/{session_id}")
async def teacher_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for teacher observers.

    Teacher connects here to:
    1. Receive real-time transcript turns as JSON messages
    2. Receive escalation notifications
    3. Send text hints that are relayed to the student session

    Message format received by teacher:
      {"type": "transcript", "speaker": "student", "text": "...", "subject": "math"}
      {"type": "escalation", "session_id": "...", "reason": "...", "teacher_ws_url": "..."}

    Message format sent by teacher:
      {"type": "hint", "text": "Try thinking about it differently..."}
    """
    await websocket.accept()
    add_teacher_connection(session_id, websocket)
    logger.info(f"Teacher connected to session {session_id}")

    try:
        # Notify teacher of connection success
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected as observer. You will receive transcript updates.",
        })

        # Listen for teacher messages (hints/injections)
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "hint":
                # Relay teacher hint back to the session (e.g., displayed to student)
                await broadcast_to_teachers(session_id, {
                    "type": "teacher_hint",
                    "session_id": session_id,
                    "text": data.get("text", ""),
                    "from": "teacher",
                })
                logger.info(f"Teacher hint relayed for session {session_id}")

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Teacher disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"Teacher WebSocket error for {session_id}: {e}")
    finally:
        remove_teacher_connection(session_id, websocket)


class EscalationRequest(BaseModel):
    session_id: str
    reason: str
    ws_base_url: str | None = None


class EscalationResponse(BaseModel):
    teacher_ws_url: str
    session_id: str


@router.post("/escalate", response_model=EscalationResponse, dependencies=[Depends(require_csrf)])
@limiter.limit("10/minute")
async def trigger_escalation(request: Request, req: EscalationRequest) -> EscalationResponse:
    """
    Trigger human escalation for a session.

    Called by the orchestrator when classifier returns 'escalate', or by
    the student frontend when the student requests human help.

    Returns the WebSocket URL that the teacher should connect to.
    """
    teacher_ws_url = await notify_escalation(
        session_id=req.session_id,
        reason=req.reason,
        ws_base_url=req.ws_base_url,
    )
    logger.info(f"Escalation triggered for session {req.session_id}: {req.reason}")
    return EscalationResponse(
        teacher_ws_url=teacher_ws_url,
        session_id=req.session_id,
    )
