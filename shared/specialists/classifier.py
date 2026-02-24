"""
Intent classifier for routing student questions to the right specialist.
Uses Claude Haiku for fast, cheap classification at temperature 0.1.
CRITICAL: Returns RoutingResult with subject string constant + confidence score.
"""
import logging
from dataclasses import dataclass
from typing import Literal
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

SubjectRoute = Literal["math", "history", "english", "escalate"]


@dataclass
class RoutingResult:
    """Result of intent classification with confidence scoring."""
    subject: SubjectRoute     # The classified subject route
    confidence: float         # 1.0=exact, 0.8=partial, 0.5=fallback
    raw_response: str         # The raw LLM output (for debugging)

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
) -> RoutingResult:
    """
    Route a student's transcript to the appropriate specialist.

    Args:
        transcript: The student's question or message
        client: Optional AsyncAnthropic client (creates new if not provided)

    Returns:
        RoutingResult with subject, confidence, and raw_response.
        - confidence=1.0: model returned exactly one of the expected words
        - confidence=0.8: route word present but with extra text
        - confidence=0.5: fallback to english (unknown response)

    CRITICAL: Use result.subject (a string constant) for routing decisions.
    Never string-match LLM output directly. Use counters for state management.
    """
    _client = client or AsyncAnthropic()

    route_map = {
        "math": "math",
        "history": "history",
        "english": "english",
        "escalate": "escalate",
    }

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

        if raw in route_map:
            confidence = 1.0           # Model responded with exactly the expected word
        elif any(r in raw for r in route_map):
            confidence = 0.8           # Route word present but with extra text
        else:
            confidence = 0.5           # Fell back to default

        subject = route_map.get(raw, "english")
        logger.info(f"Classified '{transcript[:50]}...' -> {subject} (conf={confidence})")
        return RoutingResult(subject=subject, confidence=confidence, raw_response=raw)

    except Exception as e:
        logger.error(f"Classification failed: {e}, defaulting to english")
        return RoutingResult(subject="english", confidence=0.5, raw_response="")
