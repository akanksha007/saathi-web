"""
Saathi Web Sandbox — Text-to-Speech Module.
Converts Hindi text to MP3 audio using OpenAI TTS API.
"""

import time
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, TTS_MODEL, TTS_VOICE

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def synthesize(text: str) -> tuple[bytes | None, float]:
    """
    Convert Hindi text to MP3 audio bytes.

    Args:
        text: Hindi text in Devanagari script.

    Returns:
        (mp3_bytes, latency_seconds)
    """
    if not text or not text.strip():
        return None, 0.0

    start_time = time.time()

    try:
        response = await client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="mp3",
        )

        audio_bytes = response.content
        latency = time.time() - start_time

        print(f"  🔊 TTS: \"{text[:30]}...\" ({latency:.2f}s, {len(audio_bytes)} bytes)")
        return audio_bytes, latency

    except Exception as e:
        latency = time.time() - start_time
        print(f"  ❌ TTS Error: {e}")
        return None, latency
