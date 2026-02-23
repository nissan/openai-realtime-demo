"""
Integration tests for guardrail service — requires real OPENAI_API_KEY.

These tests call the live OpenAI moderation and chat completion APIs.
They are skipped automatically when OPENAI_API_KEY is absent or set to a
test-prefixed value (handled by the autouse fixture in conftest.py).
"""
import pytest
from guardrail.service import check, check_and_rewrite, check_stream_with_sentence_buffer


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_safe_content_not_flagged():
    """Real moderation API: safe educational text is not flagged."""
    result = await check("What is the Pythagorean theorem?")
    assert not result.flagged


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_check_and_rewrite_safe_passthrough():
    """check_and_rewrite returns original text unchanged when safe."""
    text = "Explain photosynthesis."
    result = await check_and_rewrite(text)
    assert result.safe_text == text
    assert not result.flagged


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_sentence_buffer_safe_stream():
    """Sentence-buffered stream passes through safe educational text intact."""
    async def stream():
        yield "Plants use sunlight to make food. "
        yield "This process is called photosynthesis."

    chunks = [c async for c in check_stream_with_sentence_buffer(stream())]
    full = "".join(chunks)
    assert "photosynthesis" in full.lower()


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_moderation_result_has_expected_fields():
    """ModerationResult from real API has all expected fields populated."""
    result = await check("Hello, can you help me with my math homework?")
    assert hasattr(result, "flagged")
    assert hasattr(result, "categories_flagged")
    assert hasattr(result, "confidence")
    assert result.confidence >= 0.0
