"""
Saathi Web Sandbox — LLM Module.
Streams Hindi conversational responses from GPT-4o.
"""

import time
from typing import AsyncGenerator
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


async def stream_response(
    user_text: str,
    history: list[dict],
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response tokens for a Hindi conversation.

    Args:
        user_text: User's message in Hindi/Hinglish.
        history: Conversation history (list of role/content dicts).
        system_prompt: Persona-specific system prompt.

    Yields:
        Individual text tokens as they arrive.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    start_time = time.time()

    try:
        stream = await _get_client().chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            stream=True,
        )

        first_token = True
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                if first_token:
                    print(f"  🤖 LLM first token: {time.time() - start_time:.2f}s")
                    first_token = False
                yield delta.content

    except Exception as e:
        print(f"  ❌ LLM Error: {e}")
        yield "माफ़ करना, कुछ गड़बड़ हो गई। फिर से बोलो।"
