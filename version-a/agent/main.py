"""
Version A entry point: LiveKit agent workers.
Worker: learning-orchestrator (pipeline agents: Orchestrator, Math, History)
English: uses OpenAI Realtime native AgentSession (separate worker).
"""
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence default access log spam
        pass


def _start_health_server(port: int = 8080) -> None:
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server started on port {port}")


def setup_observability():
    """Initialize OTEL + Langfuse tracing."""
    from observability.langfuse import setup_langfuse_tracing
    setup_langfuse_tracing(
        service_name="version-a-agent",
        langfuse_host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
    )


async def entrypoint_orchestrator(ctx):
    """
    Main entrypoint for orchestrator + math + history pipeline agents.
    Uses GuardedAgent pattern with pre-TTS content moderation.
    """
    from livekit.agents import AgentSession
    from livekit.plugins import openai as livekit_openai, silero
    from agents.orchestrator import OrchestratorAgent
    from models.session_state import SessionUserdata

    userdata = SessionUserdata(
        room_name=ctx.room.name,
        session_id=ctx.room.name,
    )

    tts_engine = livekit_openai.TTS(model="tts-1", voice="nova")

    agent = OrchestratorAgent()

    session = AgentSession(
        userdata=userdata,
        stt=livekit_openai.STT(),
        llm=livekit_openai.LLM(model="gpt-4o-mini"),
        tts=tts_engine,
        vad=silero.VAD.load(),
    )

    await session.start(agent=agent, room=ctx.room)
    logger.info(f"Orchestrator session started in room {ctx.room.name}")

    # Insert learning session row (best-effort — failure must not break agent start)
    try:
        from services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO learning_sessions (session_id, version, room_name) "
                "VALUES ($1, 'a', $2) ON CONFLICT DO NOTHING",
                ctx.room.name, ctx.room.name,
            )
    except Exception as e:
        logger.warning(f"learning_sessions insert failed: {e}")


async def entrypoint_english(ctx):
    """
    Entrypoint for English Realtime agent.
    Uses OpenAI Realtime API natively for lower latency English tutoring.
    This is the Version A vs Version B difference for English questions.
    """
    from livekit.agents import AgentSession
    from livekit.plugins import openai as livekit_openai
    from agents.english_agent import EnglishAgent
    from models.session_state import SessionUserdata

    userdata = SessionUserdata(
        room_name=ctx.room.name,
        session_id=ctx.room.name,
        current_subject="english",
    )

    agent = EnglishAgent()

    session = AgentSession(
        userdata=userdata,
        llm=livekit_openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice="shimmer",
        ),
    )

    await session.start(agent=agent, room=ctx.room)
    logger.info(f"English Realtime session started in room {ctx.room.name}")

    # Insert learning session row (best-effort — failure must not break agent start)
    try:
        from services.transcript_store import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO learning_sessions (session_id, version, room_name) "
                "VALUES ($1, 'a', $2) ON CONFLICT DO NOTHING",
                ctx.room.name, ctx.room.name,
            )
    except Exception as e:
        logger.warning(f"learning_sessions insert failed: {e}")


if __name__ == "__main__":
    import sys
    from livekit.agents import WorkerOptions, cli, WorkerType

    setup_observability()
    _start_health_server()

    worker_type = os.environ.get("AGENT_WORKER", "orchestrator")

    if worker_type == "english":
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint_english,
                worker_type=WorkerType.ROOM,
                agent_name="learning-english",
            )
        )
    else:
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint_orchestrator,
                worker_type=WorkerType.ROOM,
                agent_name="learning-orchestrator",
            )
        )
