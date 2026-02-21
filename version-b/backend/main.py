"""Version B FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import session, orchestrator, tts, teacher
from backend.services.job_store import start_cleanup_task, stop_cleanup_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Setup OTEL tracing
    try:
        from observability.langfuse import setup_langfuse_tracing
        setup_langfuse_tracing(service_name="version-b-backend")
        logger.info("OTEL tracing configured")
    except Exception as e:
        logger.warning(f"OTEL tracing not configured: {e}")

    # Start background job cleanup
    cleanup = start_cleanup_task()
    logger.info("Background job cleanup task started")

    yield

    # Shutdown
    stop_cleanup_task()
    logger.info("Version B backend shutting down")


app = FastAPI(
    title="Voice AI Tutor — Version B Backend",
    description=(
        "FastAPI backend for Version B (OpenAI Realtime Direct). "
        "Handles orchestration, TTS streaming, and teacher escalation "
        "without LiveKit infrastructure."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend (localhost:3000) and any configured FRONTEND_URL
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    os.environ.get("FRONTEND_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(session.router)
app.include_router(orchestrator.router)
app.include_router(tts.router)
app.include_router(teacher.router)


@app.get("/health")
async def health() -> dict:
    """Health check for docker-compose depends_on."""
    return {"status": "ok", "version": "b"}


@app.get("/")
async def root() -> dict:
    return {
        "service": "version-b-backend",
        "docs": "/docs",
        "health": "/health",
    }
