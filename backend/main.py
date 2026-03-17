"""
Saathi — FastAPI Application.
Mental health companion for Hindi speakers.
Serves frontend and handles WebSocket connections, auth, and API endpoints.
"""

import json
import base64
import uuid
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from session import SessionManager
from streaming import process_audio, warm_backchannel_cache
from auth import create_token, verify_token, send_otp, verify_otp, verify_google_token
from database import init_db, close_db, db_available
from memory import maybe_generate_memory

app = FastAPI(title="Saathi")


# ─── App Lifecycle ───

@app.on_event("startup")
async def startup_event():
    """Initialize database and pre-warm caches on startup."""
    # Initialize database connection pool
    try:
        await init_db()
    except Exception as e:
        print(f"  ⚠️ Database init failed (non-fatal): {e}")

    # Pre-warm backchannel audio cache
    try:
        await warm_backchannel_cache()
    except Exception as e:
        print(f"  ⚠️ Backchannel cache warming failed (non-fatal): {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    await close_db()


# Session manager
sessions = SessionManager()


# ─── Health Check ───

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import os
    return {
        "status": "ok",
        "service": "saathi",
        "stt_ready": bool(os.getenv("OPENAI_API_KEY")),
        "llm_ready": bool(os.getenv("OPENAI_API_KEY")),
        "tts_ready": bool(os.getenv("OPENAI_API_KEY")),
        "db_ready": db_available(),
        "stt_provider": "groq" if os.getenv("GROQ_API_KEY") else "openai",
        "active_sessions": len(sessions._sessions),
    }


# ─── Auth Endpoints ───

@app.post("/auth/send-otp")
async def auth_send_otp(request: Request):
    """Send OTP to a phone number."""
    body = await request.json()
    phone = body.get("phone", "").strip()

    if not phone:
        return JSONResponse({"success": False, "message": "Phone number is required."}, status_code=400)

    # Ensure phone has country code
    if not phone.startswith("+"):
        phone = "+91" + phone  # Default to India

    result = await send_otp(phone)
    return JSONResponse(result)


@app.post("/auth/verify-otp")
async def auth_verify_otp(request: Request):
    """Verify OTP and return JWT token."""
    body = await request.json()
    phone = body.get("phone", "").strip()
    code = body.get("code", "").strip()

    if not phone or not code:
        return JSONResponse({"success": False, "message": "Phone and OTP code are required."}, status_code=400)

    if not phone.startswith("+"):
        phone = "+91" + phone

    result = await verify_otp(phone, code)
    if not result.get("success"):
        return JSONResponse(result, status_code=401)

    # Create or get user from database
    user_data = {"phone": phone}
    if db_available():
        import database as db
        user = await db.get_user_by_phone(phone)
        if not user:
            user = await db.create_user(phone=phone)
        else:
            await db.touch_user_active(user["id"])
        user_data = {
            "id": str(user["id"]),
            "phone": user["phone"],
            "name": user.get("name"),
            "age_range": user.get("age_range"),
            "onboarding_reason": user.get("onboarding_reason"),
        }
        token = create_token(str(user["id"]))
    else:
        # Fallback: generate a token with phone as identifier
        token = create_token(phone)

    return JSONResponse({
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": user_data,
    })


@app.post("/auth/google")
async def auth_google(request: Request):
    """Verify Google ID token and return JWT."""
    body = await request.json()
    id_token = body.get("id_token", "")

    if not id_token:
        return JSONResponse({"success": False, "message": "Google ID token is required."}, status_code=400)

    google_user = await verify_google_token(id_token)
    if not google_user:
        return JSONResponse({"success": False, "message": "Invalid Google token."}, status_code=401)

    user_data = google_user
    if db_available():
        import database as db
        user = await db.get_user_by_google_id(google_user["google_id"])
        if not user:
            user = await db.create_user(
                google_id=google_user["google_id"],
                name=google_user.get("name"),
            )
        else:
            await db.touch_user_active(user["id"])
        user_data = {
            "id": str(user["id"]),
            "google_id": user.get("google_id"),
            "name": user.get("name"),
            "age_range": user.get("age_range"),
            "onboarding_reason": user.get("onboarding_reason"),
        }
        token = create_token(str(user["id"]))
    else:
        token = create_token(google_user["google_id"])

    return JSONResponse({
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": user_data,
    })


@app.post("/auth/onboard")
async def auth_onboard(request: Request):
    """Complete user onboarding — save name, age, reason."""
    # Validate token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"success": False, "message": "Unauthorized."}, status_code=401)

    user_id_str = verify_token(auth_header[7:])
    if not user_id_str:
        return JSONResponse({"success": False, "message": "Invalid or expired token."}, status_code=401)

    body = await request.json()
    name = body.get("name", "").strip()
    age_range = body.get("age_range", "")
    reason = body.get("reason", "")

    if not name:
        return JSONResponse({"success": False, "message": "Name is required."}, status_code=400)

    if db_available():
        import database as db
        try:
            user_uuid = uuid.UUID(user_id_str)
            user = await db.update_user(user_uuid, name=name, age_range=age_range, onboarding_reason=reason)
            if user:
                return JSONResponse({
                    "success": True,
                    "user": {
                        "id": str(user["id"]),
                        "name": user.get("name"),
                        "age_range": user.get("age_range"),
                        "onboarding_reason": user.get("onboarding_reason"),
                    },
                })
        except Exception as e:
            print(f"  ❌ Onboarding error: {e}")

    return JSONResponse({"success": True, "user": {"name": name, "age_range": age_range}})


@app.get("/auth/me")
async def auth_me(request: Request):
    """Get current user profile."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"success": False, "message": "Unauthorized."}, status_code=401)

    user_id_str = verify_token(auth_header[7:])
    if not user_id_str:
        return JSONResponse({"success": False, "message": "Invalid or expired token."}, status_code=401)

    if db_available():
        import database as db
        try:
            user_uuid = uuid.UUID(user_id_str)
            user = await db.get_user_by_id(user_uuid)
            if user:
                return JSONResponse({
                    "success": True,
                    "user": {
                        "id": str(user["id"]),
                        "name": user.get("name"),
                        "phone": user.get("phone"),
                        "age_range": user.get("age_range"),
                        "onboarding_reason": user.get("onboarding_reason"),
                    },
                })
        except Exception:
            pass

    return JSONResponse({"success": True, "user": {"id": user_id_str}})


# ─── Frontend Serving ───

import pathlib
_backend_dir = pathlib.Path(__file__).parent
_frontend_dir = _backend_dir.parent / "frontend"

app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


@app.get("/manifest.json")
async def serve_manifest():
    """Serve PWA manifest."""
    return FileResponse(str(_frontend_dir / "manifest.json"))


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return FileResponse(str(_frontend_dir / "index.html"))


# ─── WebSocket ───

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for voice conversations."""
    await websocket.accept()
    ws_id = str(uuid.uuid4())
    print(f"\n🔗 WebSocket connected: {ws_id[:8]}")

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "start_session":
                persona = message.get("persona", "saathi")
                user_id = message.get("user_id", "anonymous")
                token = message.get("token")

                session = sessions.create(ws_id, user_id, persona)

                # If authenticated, set up DB-backed session
                if token and db_available():
                    auth_user_id = verify_token(token)
                    if auth_user_id:
                        try:
                            import database as db
                            user_uuid = uuid.UUID(auth_user_id)
                            session.user_id_uuid = user_uuid

                            # Create DB session
                            db_session = await db.create_session(user_uuid, persona)
                            session.db_session_id = db_session["id"]

                            # Load previous conversation context
                            prev_messages = await db.get_recent_messages(user_uuid, limit=10)
                            if prev_messages:
                                session.load_history(prev_messages)
                                print(f"  📚 Loaded {len(prev_messages)} previous messages")

                            # Load memory summary
                            memory = await db.get_latest_memory(user_uuid)
                            if memory:
                                session.set_memory(memory["summary"])
                                print(f"  🧠 Memory loaded: {memory['summary'][:50]}...")

                            # Update last active
                            await db.touch_user_active(user_uuid)
                        except Exception as e:
                            print(f"  ⚠️ DB session setup failed (continuing without): {e}")

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

                try:
                    await process_audio(websocket, audio_bytes, session)

                    # Save messages to DB after processing
                    if db_available() and session.db_session_id and session.history:
                        try:
                            import database as db
                            # Save the last two messages (user + assistant from this turn)
                            if len(session.history) >= 2:
                                last_user = session.history[-2]
                                last_asst = session.history[-1]
                                if last_user["role"] == "user":
                                    await db.save_message(session.db_session_id, "user", last_user["content"])
                                if last_asst["role"] == "assistant":
                                    await db.save_message(session.db_session_id, "assistant", last_asst["content"])
                        except Exception as e:
                            print(f"  ⚠️ Message save failed (non-fatal): {e}")

                except Exception as e:
                    print(f"  ❌ Pipeline error: {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Processing failed: {str(e)}",
                        })
                    except Exception:
                        pass

            elif msg_type == "mood_checkin":
                session = sessions.get(ws_id)
                mood = message.get("mood")
                timing = message.get("timing", "pre")  # "pre" or "post"

                if session and mood and isinstance(mood, int) and 1 <= mood <= 5:
                    if timing == "pre":
                        session.mood_before = mood
                    else:
                        session.mood_after = mood

                    # Save to DB
                    if db_available() and session.user_id_uuid:
                        try:
                            import database as db
                            await db.save_mood_log(
                                user_id=session.user_id_uuid,
                                mood_score=mood,
                                timing=timing,
                                session_id=session.db_session_id,
                            )
                            if timing == "pre" and session.db_session_id:
                                await db.set_session_mood_before(session.db_session_id, mood)
                            elif timing == "post" and session.db_session_id:
                                await db.set_session_mood_after(session.db_session_id, mood)
                        except Exception as e:
                            print(f"  ⚠️ Mood save failed (non-fatal): {e}")

                    print(f"  😊 Mood check-in: {timing}={mood}")
                    await websocket.send_json({
                        "type": "mood_saved",
                        "timing": timing,
                        "mood": mood,
                    })

            elif msg_type == "interrupt":
                session = sessions.get(ws_id)
                if session:
                    session.interrupted = True
                    print(f"  ⛔ User interrupted AI speech")
                    await websocket.send_json({"type": "interrupted"})

            elif msg_type == "switch_persona":
                new_persona = message.get("persona", "saathi")
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

                    # End DB session
                    if db_available() and session.db_session_id:
                        try:
                            import database as db
                            await db.end_session(
                                session.db_session_id,
                                session.turn_count,
                                session.mood_after,
                            )

                            # Trigger memory generation in background
                            if session.user_id_uuid:
                                session_count = await db.get_user_session_count(session.user_id_uuid)
                                asyncio.create_task(
                                    maybe_generate_memory(session.user_id_uuid, session_count)
                                )
                        except Exception as e:
                            print(f"  ⚠️ Session end DB update failed (non-fatal): {e}")

                sessions.remove(ws_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        session = sessions.get(ws_id)
        if session:
            print(f"  🔌 Disconnected: {session.turn_count} turns, {session.duration_seconds:.0f}s")

            # End DB session on disconnect
            if db_available() and session.db_session_id:
                try:
                    import database as db
                    await db.end_session(session.db_session_id, session.turn_count, session.mood_after)
                    if session.user_id_uuid:
                        session_count = await db.get_user_session_count(session.user_id_uuid)
                        asyncio.create_task(
                            maybe_generate_memory(session.user_id_uuid, session_count)
                        )
                except Exception:
                    pass

        sessions.remove(ws_id)
        print(f"🔗 WebSocket closed: {ws_id[:8]}")

    except Exception as e:
        print(f"  ❌ WebSocket error: {e}")
        sessions.remove(ws_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
