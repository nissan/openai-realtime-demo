"""
English specialist using GPT-4o for writing, grammar, and literature help.
Returns AsyncGenerator[str, None] for streaming responses.

Note: In Version A, English is handled by a separate OpenAI Realtime AgentSession.
In Version B, the Realtime agent handles English natively via WebRTC.
This module provides a text-only fallback for testing and non-realtime paths.
"""
import logging
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a supportive English tutor helping students with writing, grammar, and literature.
Provide constructive feedback and clear explanations.
When reviewing writing, highlight strengths before suggesting improvements.
Explain grammar rules with examples. Keep responses helpful and encouraging."""


async def answer_english_question(
    question: str,
    conversation_history: list | None = None,
    client: Optional[AsyncOpenAI] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream an English tutoring response using GPT-4o.

    Args:
        question: The student's English/writing question
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
