"""
Saathi Web Sandbox — Speech-to-Text Module.
Converts Hindi/Hinglish audio to text using OpenAI Whisper API.
"""

import os
import time
import tempfile
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, WHISPER_MODEL, WHISPER_LANGUAGE, TEMP_DIR

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
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
    temp_path = os.path.join(TEMP_DIR, f"stt_{int(time.time() * 1000)}.{ext}")

    try:
        # Write audio bytes to temp file
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # Call Whisper API
        with open(temp_path, "rb") as audio_file:
            response = await _get_client().audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                language=WHISPER_LANGUAGE,
            )

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

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
