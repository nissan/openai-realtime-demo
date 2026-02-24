"""
GuardedAgent: base class for all tutoring agents.
CRITICAL: tts_node MUST return AsyncIterable[rtc.AudioFrame], NOT str.
The sentence-level guardrail runs in tts_node before synthesis.
"""
import logging
import re
from typing import AsyncIterable, Optional

logger = logging.getLogger(__name__)

# Sentence-ending punctuation
_SENTENCE_END = re.compile(r'[.!?]+\s*')


class GuardedAgent:
    """
    Base class for tutoring agents with pre-TTS content guardrail.

    CRITICAL: tts_node must return AsyncIterable[rtc.AudioFrame].
    The guardrail intercepts text BEFORE synthesis to prevent harmful speech.

    Never return str from tts_node — agent will think but never speak.
    """

    def __init__(self, openai_client=None, **kwargs):
        self._openai_client = openai_client
        super().__init__(**kwargs)

    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings=None,
    ) -> AsyncIterable["rtc.AudioFrame"]:
        """
        Pre-TTS guardrail node. Buffers at sentence boundaries, checks content,
        then synthesizes audio.

        CRITICAL: Must return AsyncIterable[rtc.AudioFrame], NOT str.
        """
        async def _guarded_audio():
            buffer = ""

            async for chunk in text:
                buffer += chunk

                # Process complete sentences
                while True:
                    match = _SENTENCE_END.search(buffer)
                    if not match:
                        break

                    end_pos = match.end()
                    sentence = buffer[:end_pos].strip()
                    buffer = buffer[end_pos:]

                    if sentence:
                        safe_sentence = await self._guardrail_text(sentence)
                        if safe_sentence:
                            async for frame in self._synthesize(safe_sentence):
                                yield frame

            # Flush residual buffer — CRITICAL: don't drop the last fragment
            if buffer.strip():
                safe_text = await self._guardrail_text(buffer.strip())
                if safe_text:
                    async for frame in self._synthesize(safe_text):
                        yield frame

        return _guarded_audio()

    async def _guardrail_text(self, text: str, session=None) -> Optional[str]:
        """
        Check text with content moderation. Returns safe text or None if suppressed.
        Imports guardrail lazily to avoid import issues in tests.
        """
        try:
            from guardrail.service import check_and_rewrite
            result = await check_and_rewrite(text, client=self._openai_client)
            # Best-effort DB log — never breaks TTS pipeline
            try:
                from services.transcript_store import get_pool
                _session = session or (self.session if hasattr(self, "session") else None)
                session_id = (
                    _session.userdata.session_id
                    if _session and hasattr(_session, "userdata")
                    else ""
                )
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO guardrail_events "
                        "(session_id, original_text, rewritten_text, flagged, confidence, categories_flagged) "
                        "VALUES ($1, $2, $3, $4, $5, $6)",
                        session_id,
                        result.original_text,
                        result.rewritten_text or result.original_text,
                        result.flagged,
                        result.confidence,
                        result.categories_flagged,
                    )
            except Exception as db_err:
                logger.warning(f"guardrail_events insert failed: {db_err}")
            return result.safe_text
        except ImportError:
            logger.warning("Guardrail package not available, passing text through")
            return text
        except Exception as e:
            logger.error(f"Guardrail check failed: {e}, passing text through")
            return text

    async def _synthesize(self, text: str):
        """Synthesize text to audio frames. Override in subclass."""
        if hasattr(self, "_tts"):
            async for frame in self._tts.stream(text):
                yield frame
