"""
Saathi Web Sandbox — Streaming Pipeline.
Core logic: Audio → STT → LLM (streaming) → Sentence chunking → TTS → WebSocket send.
"""

import time
import base64
import json

from fastapi import WebSocket

from stt import transcribe
from llm import stream_response
from tts import synthesize
from session import Session


SENTENCE_ENDINGS = ("।", "!", "?", "।\n")
# Clause breaks — only used for chunking when buffer is long enough
CLAUSE_BREAKS = (",", "—", ":", ";", "।", "!", "?", "\n")
# Min chars before allowing a clause-break flush (increased from 15 for more natural speech)
MIN_CLAUSE_CHARS = 40
# Min chars before allowing a sentence-ending flush
MIN_SENTENCE_CHARS = 20
# Max chars before forcing a flush (even without punctuation)
MAX_BUFFER_CHARS = 120


def is_chunk_ready(buffer: str) -> bool:
    """Check if the buffer is ready to be sent to TTS.
    Prioritizes sentence endings for natural speech boundaries.
    Only splits on clause breaks (commas, etc.) when buffer is long enough
    to avoid unnaturally short fragments.
    """
    stripped = buffer.strip()
    if not stripped:
        return False
    # Always flush on sentence endings if we have a reasonable amount of text
    if len(stripped) >= MIN_SENTENCE_CHARS and stripped[-1] in SENTENCE_ENDINGS:
        return True
    # Flush on clause breaks only if buffer is getting long
    if len(stripped) >= MIN_CLAUSE_CHARS and stripped[-1] in CLAUSE_BREAKS:
        return True
    # Force flush if buffer is getting too long (but avoid mid-word splits)
    if len(stripped) >= MAX_BUFFER_CHARS:
        # Try to find the last space to avoid mid-word break
        last_space = stripped.rfind(" ", MIN_CLAUSE_CHARS)
        if last_space > 0:
            return True
        return True
    return False


async def process_audio(websocket: WebSocket, audio_bytes: bytes, session: Session):
    """
    Full streaming pipeline for one conversation turn.

    1. STT: audio → Hindi text
    2. LLM: stream tokens → detect sentence boundaries
    3. TTS: each sentence → MP3 audio
    4. Send each audio chunk to browser immediately
    """
    t0 = time.time()

    try:
        # Step 1: Speech-to-Text
        print(f"  ⏱️ STT starting...")
        text, stt_latency = await transcribe(audio_bytes)
        print(f"  ⏱️ STT done: {stt_latency:.2f}s")

        if not text:
            await websocket.send_json({
                "type": "error",
                "message": "आवाज़ समझ नहीं आई। फिर से बोलो।"
            })
            return

        # Send STT result to browser (for debug/display)
        await websocket.send_json({"type": "stt_result", "text": text})

        t1 = time.time()

        # Step 2: Stream LLM response + chunk into clauses + TTS each
        sentence_buffer = ""
        full_response = ""
        chunk_index = 0
        ttfa_logged = False
        llm_first_token_time = None

        async for token in stream_response(text, session.history, session.persona_prompt):
            if llm_first_token_time is None:
                llm_first_token_time = time.time()
                print(f"  ⏱️ LLM first token: {llm_first_token_time - t1:.2f}s after STT")

            sentence_buffer += token
            full_response += token

            # Step 3: Check for chunk boundary (clauses, not just sentences)
            if is_chunk_ready(sentence_buffer):
                sentence = sentence_buffer.strip()
                sentence_buffer = ""

                # Step 4: TTS for this chunk (with persona-specific voice)
                tts_start = time.time()
                audio_data, tts_latency = await synthesize(sentence, session.persona)
                print(f"  ⏱️ TTS chunk {chunk_index}: {tts_latency:.2f}s for '{sentence[:30]}...'")

                if audio_data:
                    # Log TTFA on first chunk
                    if not ttfa_logged:
                        ttfa = time.time() - t0
                        print(f"  ⚡ TTFA: {ttfa:.2f}s (STT:{stt_latency:.1f}s + LLM:{(llm_first_token_time - t1):.1f}s + TTS:{tts_latency:.1f}s)")
                        ttfa_logged = True

                    # Step 5: Send audio chunk to browser
                    audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                    await websocket.send_json({
                        "type": "tts_audio",
                        "audio": audio_b64,
                        "index": chunk_index,
                    })
                    chunk_index += 1

        # Flush remaining buffer (incomplete sentence at end)
        if sentence_buffer.strip():
            sentence = sentence_buffer.strip()
            audio_data, tts_latency = await synthesize(sentence, session.persona)

            if audio_data:
                if not ttfa_logged:
                    ttfa = time.time() - t0
                    print(f"  ⚡ TTFA: {ttfa:.2f}s")
                    ttfa_logged = True

                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                await websocket.send_json({
                    "type": "tts_audio",
                    "audio": audio_b64,
                    "index": chunk_index,
                })
                chunk_index += 1

        # Signal response complete
        total_time = time.time() - t0
        await websocket.send_json({
            "type": "response_complete",
            "ttfa": ttfa if ttfa_logged else total_time,
            "total_time": total_time,
            "chunks": chunk_index,
        })

        # Update session history
        session.add_turn(text, full_response)

        print(f"  ✅ Turn complete: {chunk_index} chunks, {total_time:.2f}s total")

    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Pipeline error: {str(e)}",
            })
        except Exception:
            pass
