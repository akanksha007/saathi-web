"""
Saathi — Database Module.
Async PostgreSQL data access layer using asyncpg.
Handles all CRUD operations for users, sessions, messages, mood, crisis events, and memories.
"""

import asyncpg
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from config import DATABASE_URL

# ─── Connection Pool ───

_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize the database connection pool. Call once at app startup."""
    global _pool
    if not DATABASE_URL:
        print("⚠️  DATABASE_URL not set — database features disabled.")
        return
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    print("✅ Database connection pool initialized.")


async def close_db():
    """Close the database connection pool. Call at app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("🔌 Database connection pool closed.")


def _get_pool() -> asyncpg.Pool:
    """Get the connection pool, raising if not initialized."""
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first or set DATABASE_URL.")
    return _pool


def db_available() -> bool:
    """Check if the database is configured and pool is ready."""
    return _pool is not None


# ─── Users ───

async def create_user(
    phone: Optional[str] = None,
    google_id: Optional[str] = None,
    name: Optional[str] = None,
    age_range: Optional[str] = None,
    onboarding_reason: Optional[str] = None,
) -> dict:
    """Create a new user and return their record."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO users (phone, google_id, name, age_range, onboarding_reason)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, phone, google_id, name, age_range, onboarding_reason, created_at, last_active
        """,
        phone, google_id, name, age_range, onboarding_reason,
    )
    return dict(row)


async def get_user_by_id(user_id: UUID) -> Optional[dict]:
    """Get a user by their UUID."""
    pool = _get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return dict(row) if row else None


async def get_user_by_phone(phone: str) -> Optional[dict]:
    """Get a user by phone number."""
    pool = _get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE phone = $1", phone)
    return dict(row) if row else None


async def get_user_by_google_id(google_id: str) -> Optional[dict]:
    """Get a user by Google ID."""
    pool = _get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE google_id = $1", google_id)
    return dict(row) if row else None


async def update_user(user_id: UUID, **fields) -> Optional[dict]:
    """Update user fields. Pass only the fields to update as kwargs."""
    pool = _get_pool()
    allowed = {"name", "age_range", "onboarding_reason", "last_active", "phone", "google_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return await get_user_by_id(user_id)

    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    values = [user_id] + list(updates.values())
    row = await pool.fetchrow(
        f"UPDATE users SET {set_clauses} WHERE id = $1 RETURNING *",
        *values,
    )
    return dict(row) if row else None


async def touch_user_active(user_id: UUID):
    """Update the user's last_active timestamp."""
    pool = _get_pool()
    await pool.execute(
        "UPDATE users SET last_active = NOW() WHERE id = $1",
        user_id,
    )


# ─── Sessions ───

async def create_session(user_id: UUID, persona: str) -> dict:
    """Create a new conversation session."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO sessions (user_id, persona)
        VALUES ($1, $2)
        RETURNING id, user_id, persona, started_at, ended_at, turn_count, mood_before, mood_after
        """,
        user_id, persona,
    )
    return dict(row)


async def end_session(session_id: UUID, turn_count: int, mood_after: Optional[int] = None):
    """Mark a session as ended."""
    pool = _get_pool()
    await pool.execute(
        """
        UPDATE sessions
        SET ended_at = NOW(), turn_count = $2, mood_after = $3
        WHERE id = $1
        """,
        session_id, turn_count, mood_after,
    )


async def set_session_mood_before(session_id: UUID, mood: int):
    """Set the pre-session mood score."""
    pool = _get_pool()
    await pool.execute(
        "UPDATE sessions SET mood_before = $2 WHERE id = $1",
        session_id, mood,
    )


async def set_session_mood_after(session_id: UUID, mood: int):
    """Set the post-session mood score."""
    pool = _get_pool()
    await pool.execute(
        "UPDATE sessions SET mood_after = $2 WHERE id = $1",
        session_id, mood,
    )


async def get_user_session_count(user_id: UUID) -> int:
    """Get total number of sessions for a user."""
    pool = _get_pool()
    count = await pool.fetchval(
        "SELECT COUNT(*) FROM sessions WHERE user_id = $1",
        user_id,
    )
    return count or 0


# ─── Messages ───

async def save_message(session_id: UUID, role: str, content: str) -> dict:
    """Save a single message (user or assistant) to a session."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO messages (session_id, role, content)
        VALUES ($1, $2, $3)
        RETURNING id, session_id, role, content, created_at
        """,
        session_id, role, content,
    )
    return dict(row)


async def get_recent_messages(user_id: UUID, limit: int = 10) -> list[dict]:
    """
    Get the most recent messages for a user across their latest sessions.
    Returns messages in chronological order (oldest first).
    """
    pool = _get_pool()
    rows = await pool.fetch(
        """
        SELECT m.role, m.content, m.created_at
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE s.user_id = $1
        ORDER BY m.created_at DESC
        LIMIT $2
        """,
        user_id, limit,
    )
    # Reverse to chronological order
    return [dict(r) for r in reversed(rows)]


async def get_session_messages(session_id: UUID) -> list[dict]:
    """Get all messages for a specific session in chronological order."""
    pool = _get_pool()
    rows = await pool.fetch(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE session_id = $1
        ORDER BY created_at ASC
        """,
        session_id,
    )
    return [dict(r) for r in rows]


async def get_messages_for_summary(user_id: UUID, session_limit: int = 5) -> list[dict]:
    """
    Get all messages from the user's last N sessions for memory summarization.
    Returns messages in chronological order.
    """
    pool = _get_pool()
    rows = await pool.fetch(
        """
        SELECT m.role, m.content, m.created_at
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE s.user_id = $1
          AND s.id IN (
              SELECT id FROM sessions
              WHERE user_id = $1
              ORDER BY started_at DESC
              LIMIT $2
          )
        ORDER BY m.created_at ASC
        """,
        user_id, session_limit,
    )
    return [dict(r) for r in rows]


# ─── Mood Logs ───

async def save_mood_log(
    user_id: UUID,
    mood_score: int,
    timing: str,
    session_id: Optional[UUID] = None,
    note: Optional[str] = None,
) -> dict:
    """Save a mood check-in entry."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO mood_logs (user_id, session_id, mood_score, timing, note)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, user_id, session_id, mood_score, timing, note, created_at
        """,
        user_id, session_id, mood_score, timing, note,
    )
    return dict(row)


async def get_mood_history(user_id: UUID, days: int = 30) -> list[dict]:
    """Get mood log history for a user over the last N days."""
    pool = _get_pool()
    rows = await pool.fetch(
        """
        SELECT mood_score, timing, note, created_at
        FROM mood_logs
        WHERE user_id = $1
          AND created_at >= NOW() - INTERVAL '1 day' * $2
        ORDER BY created_at DESC
        """,
        user_id, days,
    )
    return [dict(r) for r in rows]


# ─── Crisis Events ───

async def save_crisis_event(
    user_id: UUID,
    session_id: Optional[UUID],
    trigger_text: str,
    severity: str,
    helpline_shown: bool = True,
) -> dict:
    """Log a crisis detection event."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO crisis_events (user_id, session_id, trigger_text, severity, helpline_shown)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, user_id, session_id, trigger_text, severity, helpline_shown, created_at
        """,
        user_id, session_id, trigger_text, severity, helpline_shown,
    )
    return dict(row)


# ─── User Memory Summaries ───

async def save_user_memory(user_id: UUID, summary: str, session_count: int) -> dict:
    """Save a GPT-generated memory summary for a user."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO user_memories (user_id, summary, session_count)
        VALUES ($1, $2, $3)
        RETURNING id, user_id, summary, session_count, generated_at
        """,
        user_id, summary, session_count,
    )
    return dict(row)


async def get_latest_memory(user_id: UUID) -> Optional[dict]:
    """Get the most recent memory summary for a user."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        SELECT summary, session_count, generated_at
        FROM user_memories
        WHERE user_id = $1
        ORDER BY generated_at DESC
        LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None
