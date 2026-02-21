"""
Content moderation guardrail service.

CRITICAL: Sentence-level guardrail must buffer at punctuation boundaries
and flush residual at stream end. Never cut words mid-stream.
"""
import asyncio
import logging
import re
from typing import AsyncIterator, List, Optional
from openai import AsyncOpenAI

from .models import ModerationResult

logger = logging.getLogger(__name__)

# Sentence-ending punctuation pattern
_SENTENCE_END = re.compile(r'[.!?]+\s*')


async def check(text: str, client: Optional[AsyncOpenAI] = None) -> ModerationResult:
    """
    Check text for harmful content using OpenAI moderation API.

    Args:
        text: Text to check
        client: Optional AsyncOpenAI client (creates new one if not provided)

    Returns:
        ModerationResult with flagged status and categories
    """
    _client = client or AsyncOpenAI()

    try:
        response = await _client.moderations.create(input=text)
        result = response.results[0]

        flagged_categories = [
            cat for cat, flagged in result.categories.model_dump().items()
            if flagged
        ]

        return ModerationResult(
            flagged=result.flagged,
            categories_flagged=flagged_categories,
            original_text=text,
            confidence=max(result.category_scores.model_dump().values()) if result.flagged else 0.0,
        )
    except Exception as e:
        logger.error(f"Moderation check failed: {e}")
        # Fail safe: treat as not flagged on error (log for monitoring)
        return ModerationResult(
            flagged=False,
            original_text=text,
        )


async def rewrite(
    text: str,
    categories: List[str],
    client: Optional[AsyncOpenAI] = None,
) -> str:
    """
    Rewrite flagged content to be safe and educational.

    Args:
        text: Flagged text to rewrite
        categories: Categories that were flagged
        client: Optional AsyncOpenAI client

    Returns:
        Safe rewritten version of the text
    """
    _client = client or AsyncOpenAI()

    categories_str = ", ".join(categories)
    prompt = (
        f"The following educational AI response was flagged for: {categories_str}.\n"
        f"Rewrite it to be completely safe and appropriate for students, "
        f"while keeping the educational value:\n\n{text}"
    )

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a content safety editor for an educational AI tutor. "
                               "Rewrite content to be safe while preserving educational value.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        return response.choices[0].message.content or text
    except Exception as e:
        logger.error(f"Content rewrite failed: {e}")
        return "I apologize, but I cannot answer that question in the way you've asked. Please try rephrasing."


async def check_and_rewrite(
    text: str,
    client: Optional[AsyncOpenAI] = None,
) -> ModerationResult:
    """
    Check text and rewrite if flagged. Returns ModerationResult with safe_text.

    Args:
        text: Text to check and potentially rewrite
        client: Optional AsyncOpenAI client

    Returns:
        ModerationResult. Use result.safe_text for the final safe version.
    """
    result = await check(text, client)

    if result.flagged:
        safe = await rewrite(text, result.categories_flagged, client)
        result.rewritten_text = safe
        logger.warning(
            f"Content flagged ({result.categories_flagged}), rewritten. "
            f"Original: {text[:50]}..."
        )

    return result


async def check_stream_with_sentence_buffer(
    text_stream: AsyncIterator[str],
    client: Optional[AsyncOpenAI] = None,
) -> AsyncIterator[str]:
    """
    Apply guardrail to a streaming text output, buffering at sentence boundaries.

    CRITICAL: Buffer at punctuation boundaries, flush residual at end.
    Never yield partial sentences that might get cut by moderation.

    Args:
        text_stream: AsyncIterator of text chunks from LLM
        client: Optional AsyncOpenAI client

    Yields:
        Safe text chunks, one sentence at a time
    """
    buffer = ""

    async for chunk in text_stream:
        buffer += chunk

        # Look for sentence endings
        while True:
            match = _SENTENCE_END.search(buffer)
            if not match:
                break

            # Extract complete sentence
            end_pos = match.end()
            sentence = buffer[:end_pos]
            buffer = buffer[end_pos:]

            # Check and potentially rewrite this sentence
            result = await check_and_rewrite(sentence.strip(), client)
            if result.safe_text:
                yield result.safe_text + " "

    # Flush residual (critical: don't drop the last fragment)
    if buffer.strip():
        result = await check_and_rewrite(buffer.strip(), client)
        if result.safe_text:
            yield result.safe_text
