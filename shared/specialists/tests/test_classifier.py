"""Unit tests for intent classifier - all API calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


def _make_anthropic_response(text: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    return response


@pytest.mark.asyncio
async def test_route_math_question():
    """Test that math questions are routed to math."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("math")
    )

    result = await route_intent("What is 25% of 80?", client=mock_client)
    assert result.subject == "math"


@pytest.mark.asyncio
async def test_route_history_question():
    """Test that history questions are routed to history."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("history")
    )

    result = await route_intent("Why did World War I start?", client=mock_client)
    assert result.subject == "history"


@pytest.mark.asyncio
async def test_route_english_question():
    """Test that English questions are routed to english."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("english")
    )

    result = await route_intent("Help me improve this sentence.", client=mock_client)
    assert result.subject == "english"


@pytest.mark.asyncio
async def test_route_escalation():
    """Test that inappropriate content is escalated."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("escalate")
    )

    result = await route_intent("How do I hack a computer?", client=mock_client)
    assert result.subject == "escalate"


@pytest.mark.asyncio
async def test_route_unknown_defaults_to_english():
    """Test that unknown LLM output defaults to english (safe fallback)."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("unknown_gibberish")
    )

    result = await route_intent("Something weird", client=mock_client)
    assert result.subject == "english"


@pytest.mark.asyncio
async def test_route_api_failure_defaults_to_english():
    """Test that API failures default to english (safe fallback)."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

    result = await route_intent("test question", client=mock_client)
    assert result.subject == "english"


@pytest.mark.asyncio
@pytest.mark.parametrize("question,expected", [
    ("What is 2 + 2?", "math"),
    ("Solve x^2 = 4", "math"),
    ("What year did Rome fall?", "history"),
    ("Who was Napoleon?", "history"),
    ("Fix my grammar", "english"),
    ("What is a metaphor?", "english"),
])
async def test_route_parametrized(question: str, expected: str):
    """Parametrized routing test covering diverse question types."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(expected)
    )

    result = await route_intent(question, client=mock_client)
    assert result.subject == expected


@pytest.mark.asyncio
async def test_classify_exact_match_has_confidence_1():
    """Exact word response ('math') → confidence=1.0."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("math")
    )

    result = await route_intent("What is 2+2?", client=mock_client)
    assert result.subject == "math"
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_classify_partial_match_has_confidence_0_8():
    """Route word present but with extra text → confidence=0.8."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("I think math")
    )

    result = await route_intent("What is 2+2?", client=mock_client)
    assert result.subject == "english"  # "I think math" not in route_map → fallback
    assert result.confidence == 0.8     # partial match (math found in raw)


@pytest.mark.asyncio
async def test_classify_unknown_falls_back_to_english_confidence_0_5():
    """Completely unknown response → english fallback with confidence=0.5."""
    from specialists.classifier import route_intent

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response("xyzzy nonsense")
    )

    result = await route_intent("Something odd", client=mock_client)
    assert result.subject == "english"
    assert result.confidence == 0.5
