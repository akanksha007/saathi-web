"""
Saathi Web Sandbox — Text-to-Speech Module.
Converts Hindi text to MP3 audio using OpenAI TTS API.
Supports per-persona voice selection for distinct character feel.
"""

import time
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, TTS_MODEL, TTS_VOICE, TTS_VOICES

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


def get_voice_for_persona(persona: str | None) -> str:
    """Get the TTS voice for a given persona, falling back to default."""
    if persona and persona in TTS_VOICES:
        return TTS_VOICES[persona]
    return TTS_VOICE


async def synthesize(text: str, persona: str | None = None) -> tuple[bytes | None, float]:
    """
    Convert Hindi text to MP3 audio bytes.

    Args:
        text: Hindi text in Devanagari script.
        persona: Optional persona key to select the appropriate voice.

    Returns:
        (mp3_bytes, latency_seconds)
    """
    if not text or not text.strip():
        return None, 0.0

    voice = get_voice_for_persona(persona)
    start_time = time.time()

    try:
        response = await _get_client().audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=text,
            response_format="mp3",
            speed=1.0,  # Explicit speed for consistency across chunks
        )

        audio_bytes = response.content
        latency = time.time() - start_time

        print(f"  🔊 TTS ({voice}): \"{text[:30]}...\" ({latency:.2f}s, {len(audio_bytes)} bytes)")
        return audio_bytes, latency

    except Exception as e:
        latency = time.time() - start_time
        print(f"  ❌ TTS Error: {e}")
        return None, latency
