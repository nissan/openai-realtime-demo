"""
Math specialist using Claude Sonnet 4.6 for detailed mathematical reasoning.
Returns AsyncGenerator[str, None] for streaming responses.
"""
import logging
from typing import AsyncGenerator, Optional
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a friendly math tutor helping students understand mathematical concepts.
Provide clear, step-by-step explanations. Show your work. Use simple language.
When showing calculations, be explicit about each step.
Keep responses concise but complete."""


async def answer_math_question(
    question: str,
    conversation_history: list | None = None,
    client: Optional[AsyncAnthropic] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a math answer using Claude Sonnet 4.6.

    Args:
        question: The student's math question
        conversation_history: Optional list of prior messages for context
        client: Optional AsyncAnthropic client

    Yields:
        Text chunks of the response
    """
    _client = client or AsyncAnthropic()

    messages = conversation_history or []
    messages = messages + [{"role": "user", "content": question}]

    async with _client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


# Alias used by orchestrator and integration tests
stream_math_response = answer_math_question
