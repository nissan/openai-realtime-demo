"""
History specialist using GPT-4o for rich historical knowledge.
Returns AsyncGenerator[str, None] for streaming responses.
"""
import logging
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an engaging history tutor who brings the past to life for students.
Provide accurate historical context, dates, and significance.
Connect historical events to their causes and consequences.
Make history interesting and relevant. Keep responses concise but complete."""


async def answer_history_question(
    question: str,
    conversation_history: list | None = None,
    client: Optional[AsyncOpenAI] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a history answer using GPT-4o.

    Args:
        question: The student's history question
        conversation_history: Optional list of prior messages for context
        client: Optional AsyncOpenAI client

    Yields:
        Text chunks of the response
    """
    _client = client or AsyncOpenAI()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    stream = await _client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        stream=True,
        max_tokens=1024,
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# Alias used by orchestrator and integration tests
stream_history_response = answer_history_question
