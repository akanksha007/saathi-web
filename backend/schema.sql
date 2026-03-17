-- Saathi — Database Schema
-- PostgreSQL schema for mental health companion app.
-- Run this against your PostgreSQL database to create all tables.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Users ───
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE,
    google_id VARCHAR(255) UNIQUE,
    name VARCHAR(100),
    age_range VARCHAR(10),               -- '13-17', '18-24', '25-34', '35-44', '45+'
    onboarding_reason VARCHAR(50),       -- 'stress', 'loneliness', 'anxiety', 'just_talk', 'other'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Sessions ───
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona VARCHAR(20) NOT NULL,         -- 'saathi' or 'guided'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    turn_count INTEGER NOT NULL DEFAULT 0,
    mood_before INTEGER CHECK (mood_before BETWEEN 1 AND 5),
    mood_after INTEGER CHECK (mood_after BETWEEN 1 AND 5)
);

-- ─── Messages ───
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,            -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Mood Logs ───
CREATE TABLE IF NOT EXISTS mood_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    mood_score INTEGER NOT NULL CHECK (mood_score BETWEEN 1 AND 5),
    timing VARCHAR(10) NOT NULL,          -- 'pre' or 'post'
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Crisis Events ───
CREATE TABLE IF NOT EXISTS crisis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    trigger_text TEXT,                    -- anonymized excerpt that triggered detection
    severity VARCHAR(10) NOT NULL,        -- 'low', 'medium', 'critical'
    helpline_shown BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── User Memory Summaries ───
CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    session_count INTEGER NOT NULL,       -- number of sessions summarized so far
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Indexes ───
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_mood_logs_user_id ON mood_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_logs_created_at ON mood_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_events_user_id ON crisis_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_generated_at ON user_memories(generated_at DESC);
