"""Unit tests for math, history, english specialists - all API calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


async def collect_stream(gen) -> str:
    """Helper to collect all chunks from an async generator."""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return "".join(chunks)


@pytest.mark.asyncio
async def test_math_streams_response():
    """Test math specialist streams response correctly."""
    from specialists.math import answer_math_question

    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    async def mock_text_stream():
        yield "25% of 80 is "
        yield "20. "
        yield "Here's how: 0.25 x 80 = 20."

    mock_stream.text_stream = mock_text_stream()

    mock_client = AsyncMock()
    mock_client.messages.stream = MagicMock(return_value=mock_stream)

    result = await collect_stream(answer_math_question("What is 25% of 80?", client=mock_client))

    assert "20" in result
    assert len(result) > 0


@pytest.mark.asyncio
async def test_history_streams_response():
    """Test history specialist streams response correctly."""
    from specialists.history import answer_history_question

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "World War I started in 1914 "

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "due to the assassination of Archduke Franz Ferdinand."

    async def async_iter():
        yield chunk1
        yield chunk2

    mock_stream = async_iter()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

    result = await collect_stream(
        answer_history_question("Why did World War I start?", client=mock_client)
    )

    assert "1914" in result or "World War I" in result


@pytest.mark.asyncio
async def test_english_streams_response():
    """Test English specialist streams response correctly."""
    from specialists.english import answer_english_question

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "A metaphor is a figure of speech "

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "that describes something as something else."

    async def async_iter():
        yield chunk1
        yield chunk2

    mock_stream = async_iter()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

    result = await collect_stream(
        answer_english_question("Explain a metaphor", client=mock_client)
    )

    assert "metaphor" in result.lower()
