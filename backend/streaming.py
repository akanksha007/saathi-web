"""
Saathi Web Sandbox — Streaming Pipeline.
Core logic: Audio → STT → Backchannel → LLM (streaming) → Sentence chunking → Streaming TTS → WebSocket send.
Supports interruption: if session.interrupted is set, the pipeline aborts gracefully.
"""

import time
import base64
import json
import asyncio
import random

from fastapi import WebSocket

from stt import transcribe
from llm import stream_response
from tts import synthesize, synthesize_streaming
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

# Backchannel delay — only play filler if LLM takes longer than this (seconds)
BACKCHANNEL_DELAY = 1.5

# Backchannel filler phrases per persona — short sounds played while "thinking"
BACKCHANNEL_FILLERS = {
    "empathy": ["हम्म", "अच्छा"],
    "funny": ["ओहो", "अरे"],
    "angry": ["हम्म", "देखो"],
    "happy": ["वाह", "अरे"],
    "loving": ["हम्म", "बेटा"],
}
DEFAULT_FILLERS = ["हम्म", "अच्छा"]


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


async def send_backchannel(websocket: WebSocket, session: Session):
    """
    Send a short backchannel filler audio (e.g., "हम्म") while waiting for LLM.
    This makes the AI feel more present and human during the thinking phase.

    Waits BACKCHANNEL_DELAY seconds before sending — if the task is cancelled
    before the delay (because LLM responded quickly), no filler is played.
    This prevents every response from starting with "हम्म".
    """
    try:
        # Wait before sending — gives LLM a chance to respond first
        await asyncio.sleep(BACKCHANNEL_DELAY)
    except asyncio.CancelledError:
        # LLM responded quickly — no need for filler
        print(f"  💬 Backchannel skipped (LLM responded fast)")
        return

    fillers = BACKCHANNEL_FILLERS.get(session.persona, DEFAULT_FILLERS)
    filler_text = random.choice(fillers)

    try:
        # Check if we have a cached filler audio
        cache_key = f"{session.persona}:{filler_text}"
        if cache_key in _backchannel_cache:
            audio_data = _backchannel_cache[cache_key]
            latency = 0.0
        else:
            audio_data, latency = await synthesize(filler_text, session.persona)
            # Cache for future use
            if audio_data:
                _backchannel_cache[cache_key] = audio_data

        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            await websocket.send_json({
                "type": "backchannel_audio",
                "audio": audio_b64,
                "text": filler_text,
            })
            print(f"  💬 Backchannel: \"{filler_text}\" ({latency:.2f}s{', cached' if latency == 0.0 else ''})")
    except asyncio.CancelledError:
        # Cancelled during TTS synthesis — that's fine
        print(f"  💬 Backchannel cancelled during synthesis")
    except Exception as e:
        print(f"  ⚠️ Backchannel error (non-fatal): {e}")


# Cache for pre-synthesized backchannel filler audio
_backchannel_cache: dict[str, bytes] = {}


async def warm_backchannel_cache():
    """
    Pre-synthesize all backchannel filler audio at startup.
    Called once to populate the cache so fillers never need a TTS API call.
    """
    print("  🔊 Warming backchannel audio cache...")
    all_fillers = set()
    for persona, fillers in BACKCHANNEL_FILLERS.items():
        for filler_text in fillers:
            all_fillers.add((persona, filler_text))
    for filler_text in DEFAULT_FILLERS:
        all_fillers.add((None, filler_text))

    for persona, filler_text in all_fillers:
        cache_key = f"{persona}:{filler_text}"
        if cache_key not in _backchannel_cache:
            try:
                audio_data, _ = await synthesize(filler_text, persona)
                if audio_data:
                    _backchannel_cache[cache_key] = audio_data
            except Exception as e:
                print(f"  ⚠️ Failed to cache filler '{filler_text}' for {persona}: {e}")

    print(f"  ✅ Backchannel cache warmed: {len(_backchannel_cache)} fillers cached")


async def _stream_tts_chunk(websocket: WebSocket, text: str, session: Session, chunk_index: int) -> int:
    """
    Stream a single text chunk through TTS and send PCM audio sub-chunks via WebSocket.
    Returns the next chunk_index after streaming.
    Falls back to non-streaming MP3 if streaming fails.
    """
    pcm_sub_index = 0
    try:
        async for pcm_chunk in synthesize_streaming(text, session.persona, chunk_size=4096):
            if session.interrupted:
                print(f"  ⛔ TTS streaming interrupted at sub-chunk {pcm_sub_index}")
                return chunk_index

            audio_b64 = base64.b64encode(pcm_chunk).decode("utf-8")
            await websocket.send_json({
                "type": "tts_audio_stream",
                "audio": audio_b64,
                "chunk_index": chunk_index,
                "sub_index": pcm_sub_index,
                "format": "pcm",
            })
            pcm_sub_index += 1

        # Signal end of this text chunk's audio stream
        await websocket.send_json({
            "type": "tts_chunk_done",
            "chunk_index": chunk_index,
            "sub_chunks": pcm_sub_index,
        })
        return chunk_index + 1

    except Exception as e:
        print(f"  ⚠️ Streaming TTS failed, falling back to MP3: {e}")
        # Fallback to non-streaming MP3
        audio_data, tts_latency = await synthesize(text, session.persona)
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            await websocket.send_json({
                "type": "tts_audio",
                "audio": audio_b64,
                "index": chunk_index,
            })
            return chunk_index + 1
        return chunk_index


async def process_audio(websocket: WebSocket, audio_bytes: bytes, session: Session):
    """
    Full streaming pipeline for one conversation turn.

    1. STT: audio → Hindi text
    2. Backchannel: play short filler while LLM thinks
    3. LLM: stream tokens → detect sentence boundaries
    4. Streaming TTS: each sentence → PCM audio stream
    5. Send each audio sub-chunk to browser immediately
    Supports interruption: checks session.interrupted flag throughout.
    """
    t0 = time.time()
    session.interrupted = False

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

        # Step 2: Start LLM + backchannel immediately (before sending STT result)
        # This saves ~5-20ms by not waiting for the STT result websocket send
        backchannel_task = asyncio.create_task(send_backchannel(websocket, session))
        llm_stream = stream_response(text, session.history, session.persona_prompt)

        t1 = time.time()

        # Send STT result to browser (cosmetic — doesn't block the pipeline)
        await websocket.send_json({"type": "stt_result", "text": text})

        # Step 3: Stream LLM response + chunk into clauses + Streaming TTS each
        sentence_buffer = ""
        full_response = ""
        chunk_index = 0
        ttfa_logged = False
        llm_first_token_time = None

        async for token in llm_stream:
            # Check for interruption
            if session.interrupted:
                print(f"  ⛔ Pipeline interrupted during LLM streaming")
                break

            if llm_first_token_time is None:
                llm_first_token_time = time.time()
                print(f"  ⏱️ LLM first token: {llm_first_token_time - t1:.2f}s after STT")

                # Cancel backchannel if LLM responded quickly — prevents "हम्म" on every turn
                if not backchannel_task.done():
                    backchannel_task.cancel()
                    print(f"  💬 Backchannel cancelled (LLM responded in {llm_first_token_time - t1:.2f}s)")

            sentence_buffer += token
            full_response += token

            # Step 4: Check for chunk boundary
            if is_chunk_ready(sentence_buffer):
                sentence = sentence_buffer.strip()
                sentence_buffer = ""

                if session.interrupted:
                    break

                # Step 5: Stream TTS for this chunk
                tts_start = time.time()

                if not ttfa_logged:
                    ttfa = time.time() - t0
                    print(f"  ⚡ TTFA: {ttfa:.2f}s (STT:{stt_latency:.1f}s + LLM:{(llm_first_token_time - t1):.1f}s)")
                    ttfa_logged = True

                chunk_index = await _stream_tts_chunk(websocket, sentence, session, chunk_index)
                print(f"  ⏱️ TTS chunk {chunk_index - 1}: for '{sentence[:30]}...'")

                if session.interrupted:
                    break

        # Flush remaining buffer (incomplete sentence at end)
        if sentence_buffer.strip() and not session.interrupted:
            sentence = sentence_buffer.strip()

            if not ttfa_logged:
                ttfa = time.time() - t0
                print(f"  ⚡ TTFA: {ttfa:.2f}s")
                ttfa_logged = True

            chunk_index = await _stream_tts_chunk(websocket, sentence, session, chunk_index)

        # Ensure backchannel task is done (suppress CancelledError if we cancelled it)
        if not backchannel_task.done():
            backchannel_task.cancel()
            try:
                await backchannel_task
            except asyncio.CancelledError:
                pass

        # Signal response complete
        total_time = time.time() - t0
        await websocket.send_json({
            "type": "response_complete",
            "ttfa": ttfa if ttfa_logged else total_time,
            "total_time": total_time,
            "chunks": chunk_index,
            "interrupted": session.interrupted,
            "full_text": full_response,
        })

        # Update session history (even if interrupted, save partial response)
        if full_response.strip():
            session.add_turn(text, full_response)

        status = "interrupted" if session.interrupted else "complete"
        print(f"  ✅ Turn {status}: {chunk_index} chunks, {total_time:.2f}s total")

    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Pipeline error: {str(e)}",
            })
        except Exception:
            pass
