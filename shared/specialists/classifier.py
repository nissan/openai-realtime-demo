"""
Intent classifier for routing student questions to the right specialist.
Uses Claude Haiku for fast, cheap classification at temperature 0.1.
CRITICAL: Returns string constants, not LLM-generated strings (counter-based state).
"""
import logging
from typing import Literal
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

SubjectRoute = Literal["math", "history", "english", "escalate"]

SYSTEM_PROMPT = """You are a question classifier for an AI tutoring system.
Classify the student's question into exactly one category:

- math: arithmetic, algebra, geometry, calculus, statistics, any math topic
- history: historical events, dates, people, civilizations, wars, politics
- english: grammar, writing, literature, reading comprehension, language
- escalate: inappropriate content, safety concerns, or topics outside math/history/english

Respond with ONLY the single word: math, history, english, or escalate.
No explanation, no punctuation, just the single classification word."""


async def route_intent(
    transcript: str,
    client: AsyncAnthropic | None = None,
) -> SubjectRoute:
    """
    Route a student's transcript to the appropriate specialist.

    Args:
        transcript: The student's question or message
        client: Optional AsyncAnthropic client (creates new if not provided)

    Returns:
        One of: "math", "history", "english", "escalate"

    CRITICAL: Returns a string constant, never use this return value for
    string comparison with LLM output. Use counters for state management.
    """
    _client = client or AsyncAnthropic()

    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": transcript}
            ],
        )

        raw = response.content[0].text.strip().lower()

        # Map to valid route, defaulting to english if unknown
        route_map = {
            "math": "math",
            "history": "history",
            "english": "english",
            "escalate": "escalate",
        }

        route = route_map.get(raw, "english")
        logger.info(f"Classified '{transcript[:50]}...' -> {route}")
        return route

    except Exception as e:
        logger.error(f"Classification failed: {e}, defaulting to english")
        return "english"
