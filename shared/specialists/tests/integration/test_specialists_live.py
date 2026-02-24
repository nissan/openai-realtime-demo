"""
Integration tests for specialists — requires real ANTHROPIC_API_KEY and OPENAI_API_KEY.

These tests call Claude Haiku (classifier), Claude Sonnet 4.6 (math),
GPT-4o (history, english) with real API keys.
They are skipped automatically when keys are absent or test-prefixed
(handled by the autouse fixture in conftest.py).
"""
import pytest
from specialists.classifier import route_intent
from specialists.math import stream_math_response
from specialists.history import stream_history_response
from specialists.english import stream_english_response


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_classify_math():
    """Claude Haiku routes math question to 'math'."""
    result = await route_intent("What is the square root of 144?")
    assert result.subject == "math"
    assert result.confidence > 0.0


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_classify_history():
    """Claude Haiku routes history question to 'history'."""
    result = await route_intent("When did World War II end?")
    assert result.subject == "history"
    assert result.confidence > 0.0


@pytest.mark.integration
@pytest.mark.timeout(30)
async def test_classify_english():
    """Claude Haiku routes grammar question to 'english'."""
    result = await route_intent("Help me fix the grammar in this sentence.")
    assert result.subject == "english"
    assert result.confidence > 0.0


@pytest.mark.integration
@pytest.mark.timeout(60)
async def test_math_specialist_streams():
    """Claude Sonnet 4.6 streams a correct math answer."""
    chunks = [c async for c in stream_math_response("What is 25% of 80?")]
    full = "".join(chunks)
    assert "20" in full


@pytest.mark.integration
@pytest.mark.timeout(60)
async def test_history_specialist_streams():
    """GPT-4o streams a history answer containing relevant content."""
    chunks = [c async for c in stream_history_response("Who was Julius Caesar?")]
    full = "".join(chunks)
    assert len(full) > 20


@pytest.mark.integration
@pytest.mark.timeout(60)
async def test_english_specialist_streams():
    """GPT-4o streams an English/writing answer."""
    chunks = [c async for c in stream_english_response("What is a metaphor?")]
    full = "".join(chunks)
    assert "metaphor" in full.lower()
