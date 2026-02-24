"""
TTS streaming router for Version B.

POST /tts/stream → streams chunked PCM audio from OpenAI TTS.

CRITICAL: Stream chunks as they arrive — NEVER buffer the full response.
Client plays chunks via Web Audio API while backend is still generating.

Version B tradeoff vs Version A:
- Version A: TTS runs inside LiveKit pipeline node (GuardedAgent.tts_node)
  returns AsyncIterable[rtc.AudioFrame] — pre-guardrailed at synthesis time
- Version B: Guardrail runs in orchestrator before TTS; TTS gets clean text,
  streams raw PCM to client which plays via Web Audio API
"""
import asyncio
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI

from backend.routers.csrf import require_csrf
from backend.services.job_store import get_job
from backend.models.job import JobStatus

router = APIRouter(prefix="/tts", tags=["tts"])
logger = logging.getLogger(__name__)

_openai: AsyncOpenAI | None = None
TTS_CHUNK_SIZE = 4096  # bytes per chunk (~128ms at 16kHz PCM16)


def get_openai_client() -> AsyncOpenAI:
    global _openai
    if _openai is None:
        _openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai


class TtsStreamRequest(BaseModel):
    job_id: str
    voice: str = "alloy"


@router.post("/stream", dependencies=[Depends(require_csrf)])
async def stream_tts(req: TtsStreamRequest) -> StreamingResponse:
    """
    Stream TTS audio for a completed orchestration job.

    Client calls this after polling GET /orchestrate/{job_id} returns tts_ready=True.
    Returns chunked PCM16 at 24kHz mono — client feeds into Web Audio API buffer.

    Audio flow (Version B):
    1. Student speaks → OpenAI Realtime WebRTC (filler phrases via Realtime)
    2. Backend orchestrates, guardrails text, sets tts_ready=True on job
    3. Client mutes Realtime audio, calls POST /tts/stream
    4. This endpoint streams PCM chunks → client decodes + plays
    5. On stream end, client unmutes Realtime audio (50ms crossfade)
    """
    job = get_job(req.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.ERROR:
        raise HTTPException(status_code=422, detail=job.error_message or "Job failed")

    if not job.tts_ready or not job.safe_text:
        raise HTTPException(status_code=409, detail="Job not ready for TTS")

    return StreamingResponse(
        _stream_audio_chunks(job.safe_text, req.voice),
        media_type="audio/pcm",
        headers={
            "X-Audio-Sample-Rate": "24000",
            "X-Audio-Channels": "1",
            "X-Audio-Bit-Depth": "16",
        },
    )


async def _stream_audio_chunks(text: str, voice: str):
    """
    Stream PCM16 audio from OpenAI TTS.

    CRITICAL: Use response.iter_bytes() and yield as chunks arrive.
    Never accumulate into a list or bytes object before yielding.
    """
    client = get_openai_client()
    try:
        async with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="pcm",  # Raw PCM16 @ 24kHz mono
        ) as response:
            async for chunk in response.iter_bytes(chunk_size=TTS_CHUNK_SIZE):
                if chunk:
                    yield chunk
                    # Yield control to event loop between chunks
                    await asyncio.sleep(0)
    except Exception as e:
        logger.error(f"TTS streaming error: {e}")
        # Can't raise HTTPException inside a streaming response generator
        # Client will see a truncated stream and should handle gracefully
