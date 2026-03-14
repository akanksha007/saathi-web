"""
Saathi Web Sandbox — FastAPI Application.
Serves frontend and handles WebSocket connections for voice conversations.
"""

import json
import base64
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from session import SessionManager
from streaming import process_audio

app = FastAPI(title="Saathi Web Sandbox")

# Session manager
sessions = SessionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint — useful for debugging on Railway."""
    import os
    # Re-read env var fresh at request time (not cached from startup)
    raw_env = os.environ.get("OPENAI_API_KEY")

    # Also check config module
    from config import OPENAI_API_KEY as config_key

    # Railway metadata to verify which deployment we're on
    git_sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown")
    service_name = os.environ.get("RAILWAY_SERVICE_NAME", "unknown")
    deploy_id = os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown")

    # List ALL env var names (not values) to see what Railway injects
    all_env_names = sorted(os.environ.keys())

    return {
        "status": "ok",
        "deploy_id": deploy_id[:12],
        "git_sha": git_sha[:8],
        "service_name": service_name,
        "config_key_set": bool(config_key),
        "raw_env_key_set": bool(raw_env),
        "raw_env_preview": f"{raw_env[:8]}..." if raw_env else None,
        "total_env_vars": len(all_env_names),
        "all_env_var_names": all_env_names,
    }

# Resolve frontend path (works both locally and in Docker)
import pathlib
_backend_dir = pathlib.Path(__file__).parent
_frontend_dir = _backend_dir.parent / "frontend"

# Serve frontend static files
app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return FileResponse(str(_frontend_dir / "index.html"))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for voice conversations."""
    await websocket.accept()
    ws_id = str(uuid.uuid4())
    print(f"\n🔗 WebSocket connected: {ws_id[:8]}")

    try:
        while True:
            # Receive message
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "start_session":
                persona = message.get("persona", "empathy")
                user_id = message.get("user_id", "anonymous")
                session = sessions.create(ws_id, user_id, persona)
                print(f"  📋 Session started: persona={persona}, user={user_id[:8]}")
                await websocket.send_json({
                    "type": "session_started",
                    "persona": persona,
                })

            elif msg_type == "audio_data":
                session = sessions.get(ws_id)
                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active session. Select a persona first.",
                    })
                    continue

                # Decode base64 audio
                audio_b64 = message.get("audio", "")
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid audio data.",
                    })
                    continue

                if len(audio_bytes) < 1000:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Audio too short.",
                    })
                    continue

                print(f"\n  🎤 Audio received: {len(audio_bytes)} bytes")

                # Process through streaming pipeline
                try:
                    await process_audio(websocket, audio_bytes, session)
                except Exception as e:
                    print(f"  ❌ Pipeline error: {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Processing failed: {str(e)}",
                        })
                    except Exception:
                        pass

            elif msg_type == "switch_persona":
                new_persona = message.get("persona", "empathy")
                session = sessions.get(ws_id)
                if session:
                    session.reset(new_persona)
                    print(f"  🔄 Persona switched to: {new_persona}")
                    await websocket.send_json({
                        "type": "session_started",
                        "persona": new_persona,
                    })

            elif msg_type == "end_session":
                session = sessions.get(ws_id)
                if session:
                    print(f"  👋 Session ended: {session.turn_count} turns, {session.duration_seconds:.0f}s")
                sessions.remove(ws_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        session = sessions.get(ws_id)
        if session:
            print(f"  🔌 Disconnected: {session.turn_count} turns, {session.duration_seconds:.0f}s")
        sessions.remove(ws_id)
        print(f"🔗 WebSocket closed: {ws_id[:8]}")

    except Exception as e:
        print(f"  ❌ WebSocket error: {e}")
        sessions.remove(ws_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
