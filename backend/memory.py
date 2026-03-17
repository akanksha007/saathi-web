"""
Saathi — Memory Summarization Module.
Generates GPT-based user memory summaries from past conversations.
These summaries are injected into the system prompt so Saathi 'remembers' the user.
"""

import asyncio
from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI
from config import OPENAI_API_KEY, LLM_MODEL

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


SUMMARY_SYSTEM_PROMPT = """तुम एक AI assistant हो जो conversations को summarize करता है।

नीचे एक user और Saathi (एक AI wellness companion) के बीच की recent बातचीत है।
इसका एक छोटा summary बनाओ (दो से तीन वाक्य, Hindi में) जो बताए:
- User कौन है (age, situation, context)
- उनकी recurring themes क्या हैं (stress, loneliness, relationship issues, etc.)
- Important life details जो पता चली
- उनका emotional pattern कैसा है

Summary ऐसे लिखो जैसे एक दोस्त को दूसरे दोस्त के बारे में बता रहे हो।

उदाहरण:
"यह user college student है, exam stress से परेशान है। पिछली बार boyfriend से लड़ाई की बात कर रहे थे। अक्सर रात को अकेला महसूस करते हैं लेकिन बात करने के बाद better feel करते हैं।"

सिर्फ summary दो, कोई और text नहीं।"""


async def generate_memory_summary(messages: list[dict]) -> Optional[str]:
    """
    Generate a memory summary from a list of conversation messages.

    Args:
        messages: List of dicts with 'role' and 'content' keys,
                  from the user's last several sessions.

    Returns:
        A 2-3 line Hindi summary string, or None if generation fails.
    """
    if not messages:
        return None

    # Format conversation for the summarizer
    conversation_text = ""
    for msg in messages:
        role_label = "User" if msg["role"] == "user" else "Saathi"
        conversation_text += f"{role_label}: {msg['content']}\n"

    # Truncate if too long (keep last ~4000 chars to stay within context)
    if len(conversation_text) > 4000:
        conversation_text = conversation_text[-4000:]

    try:
        response = await _get_client().chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            max_tokens=200,
            temperature=0.5,
        )
        summary = response.choices[0].message.content.strip()
        print(f"  🧠 Memory summary generated: {summary[:80]}...")
        return summary

    except Exception as e:
        print(f"  ❌ Memory summary generation failed: {e}")
        return None


async def maybe_generate_memory(user_id: UUID, session_count: int):
    """
    Check if a memory summary should be generated (every 5 sessions)
    and generate one if needed. Runs as a background task.

    Args:
        user_id: The user's database UUID.
        session_count: Total number of sessions the user has had.
    """
    # Generate memory every 5 sessions
    if session_count < 5 or session_count % 5 != 0:
        return

    try:
        from database import db_available, get_messages_for_summary, save_user_memory

        if not db_available():
            return

        messages = await get_messages_for_summary(user_id, session_limit=5)
        if not messages:
            return

        summary = await generate_memory_summary(messages)
        if summary:
            await save_user_memory(user_id, summary, session_count)
            print(f"  🧠 Memory saved for user {str(user_id)[:8]} (session #{session_count})")

    except Exception as e:
        print(f"  ⚠️ Memory generation failed (non-fatal): {e}")
