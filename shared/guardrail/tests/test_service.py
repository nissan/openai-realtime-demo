"""Unit tests for guardrail service - all API calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from guardrail.models import ModerationResult


@pytest.fixture
def safe_moderation_response():
    """Mock OpenAI moderation response - not flagged."""
    result = MagicMock()
    result.flagged = False
    result.categories = MagicMock()
    result.categories.model_dump.return_value = {
        "sexual": False, "violence": False, "hate": False,
        "harassment": False, "self_harm": False,
    }
    result.category_scores = MagicMock()
    result.category_scores.model_dump.return_value = {
        "sexual": 0.01, "violence": 0.01, "hate": 0.01,
        "harassment": 0.01, "self_harm": 0.01,
    }
    response = MagicMock()
    response.results = [result]
    return response


@pytest.fixture
def flagged_moderation_response():
    """Mock OpenAI moderation response - flagged for violence."""
    result = MagicMock()
    result.flagged = True
    result.categories = MagicMock()
    result.categories.model_dump.return_value = {
        "sexual": False, "violence": True, "hate": False,
        "harassment": False, "self_harm": False,
    }
    result.category_scores = MagicMock()
    result.category_scores.model_dump.return_value = {
        "sexual": 0.01, "violence": 0.95, "hate": 0.01,
        "harassment": 0.01, "self_harm": 0.01,
    }
    response = MagicMock()
    response.results = [result]
    return response


@pytest.mark.asyncio
async def test_check_safe_content(safe_moderation_response):
    """Test that safe content is not flagged."""
    from guardrail.service import check

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(return_value=safe_moderation_response)

    result = await check("What is 25% of 80?", client=mock_client)

    assert not result.flagged
    assert result.categories_flagged == []
    assert result.original_text == "What is 25% of 80?"


@pytest.mark.asyncio
async def test_check_flagged_content(flagged_moderation_response):
    """Test that harmful content is correctly flagged."""
    from guardrail.service import check

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(return_value=flagged_moderation_response)

    result = await check("How to make a bomb?", client=mock_client)

    assert result.flagged
    assert "violence" in result.categories_flagged
    assert result.confidence > 0.9


@pytest.mark.asyncio
async def test_rewrite_flagged_content():
    """Test that flagged content is rewritten safely."""
    from guardrail.service import rewrite

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I cannot help with that topic."

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await rewrite("harmful text", ["violence"], client=mock_client)

    assert result == "I cannot help with that topic."
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_check_and_rewrite_safe(safe_moderation_response):
    """Test check_and_rewrite with safe content - no rewrite needed."""
    from guardrail.service import check_and_rewrite

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(return_value=safe_moderation_response)

    result = await check_and_rewrite("What is 25% of 80?", client=mock_client)

    assert not result.flagged
    assert result.rewritten_text is None
    assert result.safe_text == "What is 25% of 80?"


@pytest.mark.asyncio
async def test_check_and_rewrite_flagged(flagged_moderation_response):
    """Test check_and_rewrite with flagged content - rewrite occurs."""
    from guardrail.service import check_and_rewrite

    mock_rewrite_response = MagicMock()
    mock_rewrite_response.choices = [MagicMock()]
    mock_rewrite_response.choices[0].message.content = "Safe educational response."

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(return_value=flagged_moderation_response)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_rewrite_response)

    result = await check_and_rewrite("harmful content", client=mock_client)

    assert result.flagged
    assert result.rewritten_text == "Safe educational response."
    assert result.safe_text == "Safe educational response."


@pytest.mark.asyncio
async def test_sentence_buffer_flushes_residual():
    """Test that sentence buffer flushes residual text at stream end."""
    from guardrail.service import check_stream_with_sentence_buffer

    safe_response = MagicMock()
    safe_response.results = [MagicMock()]
    safe_response.results[0].flagged = False
    safe_response.results[0].categories = MagicMock()
    safe_response.results[0].categories.model_dump.return_value = {}
    safe_response.results[0].category_scores = MagicMock()
    safe_response.results[0].category_scores.model_dump.return_value = {}

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(return_value=safe_response)

    async def text_stream():
        yield "Hello world"
        yield ". This is a test"
        yield ". Final fragment without punctuation"

    results = []
    async for chunk in check_stream_with_sentence_buffer(text_stream(), client=mock_client):
        results.append(chunk)

    full_text = "".join(results)
    # Residual "Final fragment without punctuation" should be flushed
    assert "Final fragment" in full_text


@pytest.mark.asyncio
async def test_check_api_failure_is_safe():
    """Test that API failures fail safely (not flagged)."""
    from guardrail.service import check

    mock_client = AsyncMock()
    mock_client.moderations.create = AsyncMock(side_effect=Exception("API error"))

    result = await check("test text", client=mock_client)

    # Fail safe: not flagged on error
    assert not result.flagged


def test_moderation_result_safe_text_unflagged():
    """Test safe_text returns original when not flagged."""
    result = ModerationResult(
        flagged=False,
        original_text="Safe content",
    )
    assert result.safe_text == "Safe content"


def test_moderation_result_safe_text_flagged_with_rewrite():
    """Test safe_text returns rewrite when flagged."""
    result = ModerationResult(
        flagged=True,
        original_text="Harmful content",
        rewritten_text="Safe version",
    )
    assert result.safe_text == "Safe version"
