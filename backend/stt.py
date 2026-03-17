"""
Saathi Web Sandbox — Speech-to-Text Module.
Converts Hindi/Hinglish audio to text using Groq Whisper (fast) or OpenAI Whisper.
"""

import os
import io
import time
import tempfile
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, GROQ_API_KEY, STT_PROVIDER, WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_PROMPT, TEMP_DIR

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if STT_PROVIDER == "groq":
            _client = AsyncOpenAI(
                api_key=GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            print("  🎤 STT: Using Groq Whisper (fast)")
        else:
            _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            print("  🎤 STT: Using OpenAI Whisper")
    return _client


async def transcribe(audio_bytes: bytes) -> tuple[str | None, float]:
    """
    Transcribe Hindi/Hinglish audio bytes to text.

    Args:
        audio_bytes: WAV audio data.

    Returns:
        (transcribed_text, latency_seconds)
    """
    if not audio_bytes:
        return None, 0.0

    start_time = time.time()
    # Detect format from audio bytes (WAV starts with RIFF, WebM with 0x1A45DFA3)
    ext = "wav"
    if audio_bytes[:4] != b"RIFF":
        ext = "webm"

    try:
        # Use in-memory BytesIO buffer instead of temp file for lower latency
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{ext}"  # OpenAI API needs a filename with extension

        # Build API params — only include language if explicitly set
        api_params = {
            "model": WHISPER_MODEL,
            "file": audio_file,
            "prompt": WHISPER_PROMPT,
        }
        if WHISPER_LANGUAGE:
            api_params["language"] = WHISPER_LANGUAGE
        response = await _get_client().audio.transcriptions.create(**api_params)

        latency = time.time() - start_time
        text = response.text.strip()

        if not text:
            return None, latency

        print(f"  📝 STT: \"{text}\" ({latency:.2f}s)")
        return text, latency

    except Exception as e:
        latency = time.time() - start_time
        print(f"  ❌ STT Error: {e}")
        return None, latency
