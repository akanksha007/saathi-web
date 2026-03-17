# 🛠️ Saathi MVP Implementation Tasks — First 10 Customers

> **Scope:** All features needed to acquire the first 10 paying customers, **excluding payment/billing logic**.
> **Derived from:** ROADMAP_PATH_B.md (Phases 0, 1, 2 — cherry-picked)
> **Current State:** Voice pipeline works (STT → LLM → TTS), 5 fun personas, in-memory sessions, no auth/persistence/safety.

---

## Overview: What Exists vs. What Needs to Be Built

| Area | Current State | Target State |
|------|--------------|--------------|
| Personas | 5 fun personalities (empathy, funny, angry, happy, loving) | 2 therapy-informed companions (Saathi, Didi/Bhaiya) |
| Auth | Anonymous (`localStorage` UUID) | Phone OTP + Google Sign-In |
| Database | In-memory Python dict | PostgreSQL (Supabase/Railway) |
| Conversation Memory | Ephemeral (lost on refresh) | Persistent + GPT-generated user summaries |
| Mood Tracking | None | Pre/post session emoji check-in |
| Safety | None | Crisis keyword detection + helpline routing + disclaimers |
| Session Management | `session.py` — in-memory `SessionManager` | DB-backed sessions with user association |

---

## TASK 1: Safety & Crisis Detection System
**Priority:** 🔴 CRITICAL — Non-negotiable before any public launch
**Phase:** 0.3
**Estimated Effort:** 3-4 days

### 1.1 — Crisis Keyword Detection Engine
**File:** `backend/crisis.py` (new)

- [ ] Create a crisis keyword list covering:
  - Hindi: आत्महत्या, मरना चाहता हूँ, जीने का मन नहीं, ज़िंदगी से तंग, मर जाऊँ, ख़ुदकुशी, फाँसी, ज़हर, नींद की गोली, कलाई काट
  - Hinglish: suicide, mar jana chahta hu, jeene ka mann nahi, zindagi se tang, khatam karna chahta hu
  - Transliterated: aatmahatya, marna chahta, jeena nahi chahta, khatam kar dena
- [ ] Build a `detect_crisis(text: str) -> CrisisResult` function that:
  - Scans STT output against keyword list (fuzzy matching for Hindi transliteration variants)
  - Returns severity level (low/medium/critical) and matched keywords
  - Handles negation context (e.g., "मैं suicide नहीं करूँगा" should be flagged but as lower severity)

### 1.2 — Crisis Response Flow
**Files:** `backend/streaming.py` (modify), `backend/crisis.py` (new), `frontend/app.js` (modify)

- [ ] Integrate crisis detection into `process_audio()` in `streaming.py`:
  - After STT transcription, run `detect_crisis()` on the text
  - If crisis detected: break the normal LLM flow
- [ ] Crisis response protocol:
  - Send a special WebSocket message: `{ type: "crisis_detected", severity: "...", helplines: [...] }`
  - Generate a compassionate voice response via TTS: "मैं समझ रहा हूँ कि तुम बहुत मुश्किल में हो। अभी Vandrevala Foundation helpline पर call करो: 1860-2662-345। वो ज़रूर मदद करेंगे।"
  - Display helpline numbers on screen (frontend overlay)
- [ ] Helplines to integrate:
  - iCall: 9152987821
  - Vandrevala Foundation: 1860-2662-345
  - AASRA: 9820466726
- [ ] After crisis response: block further AI interaction until user acknowledges they've seen the helpline info

### 1.3 — Legal Disclaimers
**Files:** `frontend/index.html` (modify), `backend/personas.py` (modify)

- [ ] Add disclaimer banner to every screen in `index.html`:
  - Hindi: "साथी एक AI दोस्त है, therapist नहीं। गंभीर समस्या में professional help लें।"
  - English: "Saathi is an AI companion, not a licensed therapist. Seek professional help for serious concerns."
- [ ] Add disclaimer to system prompts in `personas.py`:
  - Inject into BASE_RULES: "If someone asks if you're a real therapist, clearly state you're an AI companion and recommend professional help."
- [ ] Add disclaimer to the first voice interaction of every new session (spoken by Saathi)
- [ ] Add a persistent small disclaimer footer in the conversation screen

### 1.4 — Crisis Event Logging
**File:** `backend/crisis.py` (new), `backend/database.py` (new — see Task 4)

- [ ] Log every crisis event to `crisis_events` table:
  - `id`, `user_id`, `session_id`, `trigger_text` (anonymized), `severity`, `timestamp`, `helpline_shown`
- [ ] Ensure crisis logs are reviewable (admin query or simple script)

---

## TASK 2: Therapy-Informed Personas
**Priority:** 🔴 HIGH — Core product identity
**Phase:** 0.2
**Estimated Effort:** 2-3 days

### 2.1 — Replace Persona System Prompts
**File:** `backend/personas.py` (rewrite)

- [ ] Replace all 5 current personas with 2 new therapy-informed personas:

**Persona 1 — "साथी" (Saathi) — Default**
  - Style: Warm, patient, gently curious friend
  - Framework: Rogerian (person-centered) + Active Listening
  - Behaviors: Asks "और बताओ?", validates feelings, never judges, reflects back emotions
  - Fillers: "हम्म", "अच्छा", "हाँ हाँ, बताओ"
  - Voice: `nova` (warm, gentle)

**Persona 2 — "दीदी/भैया" (Didi/Bhaiya) — Guided**
  - Style: Slightly more structured, offers techniques
  - Framework: CBT-lite + Motivational Interviewing
  - Behaviors: Offers breathing exercises, reframing techniques, journaling prompts
  - Fillers: "सुनो", "चलो try करते हैं", "एक काम करो"
  - Voice: `shimmer` (calm, guiding)

- [ ] Update `BASE_RULES` to include:
  - Therapy-informed guardrails (don't diagnose, don't prescribe medication)
  - Emotional validation patterns
  - De-escalation language for distressed users
  - Disclaimer injection: "I'm an AI friend, not a therapist"

### 2.2 — Update TTS Voice Mapping
**File:** `backend/config.py` (modify)

- [ ] Update `TTS_VOICES` dict to map new personas:
  ```python
  TTS_VOICES = {
      "saathi": "nova",      # Warm, gentle — person-centered companion
      "guided": "shimmer",   # Calm, structured — CBT-lite guide
  }
  ```
- [ ] Update `BACKCHANNEL_FILLERS` in `streaming.py` for new personas

### 2.3 — Update Frontend Persona Selection
**Files:** `frontend/index.html` (modify), `frontend/app.js` (modify)

- [ ] Replace the 5 persona cards with 2 new cards:
  - **साथी** — "दिल की बात सुनेगा, समझेगा" / "Your compassionate listener"
  - **दीदी/भैया** — "तरीके सिखाएगा, guide करेगा" / "Your wellness guide"
- [ ] Update `PERSONA_LABELS`, `PERSONA_AVATAR_LETTERS`, `PERSONA_AVATAR_COLORS` in `app.js`
- [ ] Update persona card CSS classes and styling in `style.css`
- [ ] Update the hero explainer text to reflect mental health positioning:
  - "अपने मन की बात करो। साथी सुनेगा।" (Share what's on your mind. Saathi will listen.)

---

## TASK 3: User Authentication
**Priority:** 🔴 HIGH — Required for persistence, memory, everything
**Phase:** 1.1
**Estimated Effort:** 4-5 days

### 3.1 — Backend Auth System
**File:** `backend/auth.py` (new)

- [ ] Phone + OTP authentication:
  - Integrate MSG91 or Twilio Verify for OTP delivery
  - API endpoints:
    - `POST /auth/send-otp` — accepts phone number, sends OTP
    - `POST /auth/verify-otp` — accepts phone + OTP, returns JWT token
    - `POST /auth/refresh` — refresh expired JWT
    - `GET /auth/me` — get current user profile
  - Rate limiting: max 3 OTP requests per phone per 10 minutes
- [ ] Google Sign-In (secondary):
  - `POST /auth/google` — accepts Google ID token, verifies, returns JWT
- [ ] JWT token management:
  - Issue JWT on successful auth (short-lived: 7 days)
  - Middleware to validate JWT on protected endpoints
  - Store token in `localStorage` on frontend

### 3.2 — User Onboarding Flow
**Files:** `frontend/index.html` (modify), `frontend/app.js` (modify), `frontend/auth.js` (new)

- [ ] New screen: Login/Register (before persona selection)
  - Phone number input with country code (+91 default)
  - OTP input (6-digit)
  - "Google से login करें" button
- [ ] New screen: Simple onboarding (after first login only)
  - First name (required)
  - Age range dropdown: 13-17, 18-24, 25-34, 35-44, 45+
  - "What brings you here?" dropdown: stress, loneliness, anxiety, just want to talk, other
- [ ] Store auth token in `localStorage`, auto-login on return visits
- [ ] Show user name in conversation header after login

### 3.3 — WebSocket Authentication
**File:** `backend/main.py` (modify)

- [ ] Modify WebSocket endpoint to accept auth token:
  - Pass JWT as query param: `/ws?token=xxx` or in first message
  - Validate token and associate session with authenticated user
  - Reject unauthenticated connections (or allow limited anonymous usage)
- [ ] Update `SessionManager` to link sessions to authenticated `user_id` from database

---

## TASK 4: PostgreSQL Database
**Priority:** 🔴 HIGH — Foundation for persistence
**Phase:** 1.2
**Estimated Effort:** 2-3 days

### 4.1 — Database Setup
**File:** `backend/database.py` (new)

- [ ] Set up PostgreSQL connection via Supabase or Railway Postgres
- [ ] Use `asyncpg` or `SQLAlchemy` async for database operations
- [ ] Add database URL to `config.py` and `.env.example`:
  ```
  DATABASE_URL=postgresql://user:pass@host:5432/saathi
  ```
- [ ] Connection pooling setup (min 2, max 10 connections)

### 4.2 — Schema & Migrations
**File:** `backend/migrations/` (new directory), `backend/schema.sql` (new)

- [ ] Create minimal schema:
  ```sql
  -- Users
  users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE,
    google_id VARCHAR(255) UNIQUE,
    name VARCHAR(100),
    age_range VARCHAR(10),
    onboarding_reason VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW()
  )

  -- Sessions
  sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    persona VARCHAR(20),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    turn_count INTEGER DEFAULT 0,
    mood_before INTEGER,  -- 1-5
    mood_after INTEGER    -- 1-5
  )

  -- Messages
  messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(10),  -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
  )

  -- Mood Logs
  mood_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    mood_score INTEGER CHECK (mood_score BETWEEN 1 AND 5),
    note TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
  )

  -- Crisis Events
  crisis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID REFERENCES sessions(id),
    trigger_text TEXT,  -- anonymized
    severity VARCHAR(10),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    helpline_shown BOOLEAN DEFAULT FALSE
  )

  -- User Memory Summaries
  user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    summary TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    session_count INTEGER  -- number of sessions summarized
  )
  ```
- [ ] Create migration script (or use Alembic for versioned migrations)
- [ ] Add indexes: `users.phone`, `sessions.user_id`, `messages.session_id`, `mood_logs.user_id`

### 4.3 — Data Access Layer
**File:** `backend/database.py` (new)

- [ ] CRUD functions:
  - `create_user(phone, name, age_range, reason) -> User`
  - `get_user_by_phone(phone) -> User`
  - `get_user_by_id(user_id) -> User`
  - `create_session(user_id, persona) -> Session`
  - `end_session(session_id, mood_after) -> None`
  - `save_message(session_id, role, content) -> None`
  - `get_recent_messages(user_id, limit=10) -> list[Message]`
  - `save_mood_log(user_id, mood_score, note) -> None`
  - `get_mood_history(user_id, days=30) -> list[MoodLog]`
  - `save_crisis_event(user_id, session_id, trigger_text, severity) -> None`
  - `save_user_memory(user_id, summary, session_count) -> None`
  - `get_latest_memory(user_id) -> UserMemory`

---

## TASK 5: Persistent Conversation Memory
**Priority:** 🔴 HIGH — THE retention unlock
**Phase:** 1.3
**Estimated Effort:** 3-4 days

### 5.1 — Save Conversations to Database
**Files:** `backend/streaming.py` (modify), `backend/session.py` (modify)

- [ ] Modify `process_audio()` to save each message to the database:
  - After STT: `save_message(session_id, "user", text)`
  - After full LLM response: `save_message(session_id, "assistant", full_response)`
- [ ] Modify `Session` class to hold a database `session_id` (UUID)
- [ ] On session start: create a database session record via `create_session()`
- [ ] On session end / disconnect: call `end_session()` to record `ended_at`

### 5.2 — Load Previous Context on New Session
**Files:** `backend/session.py` (modify), `backend/main.py` (modify)

- [ ] When a user starts a new session:
  1. Load last 10 messages from their most recent session from DB
  2. Inject them into `session.history` so the LLM has context
  3. Load the latest `user_memory` summary (if exists) and prepend to system prompt
- [ ] This makes Saathi "remember" the user across browser refreshes and devices

### 5.3 — GPT-Based Memory Summarization
**File:** `backend/memory.py` (new)

- [ ] After every 5 sessions for a user, generate a memory summary:
  - Fetch all messages from the last 5 sessions
  - Send to GPT-4o-mini with a summarization prompt:
    ```
    Below are recent conversations between a user and Saathi (an AI wellness companion).
    Generate a 2-3 line summary in Hindi of what Saathi knows about this user.
    Include: their situation, recurring themes, emotional patterns, and important life details.
    Example: "यह user college student है, exam stress से परेशान है, पिछली बार boyfriend से लड़ाई की बात कर रहे थे।"
    ```
  - Save summary to `user_memories` table
- [ ] Inject latest memory summary into the system prompt at session start:
  - Add a section: "तुम्हें इस user के बारे में यह पता है: {memory_summary}"
- [ ] Run summarization as a background task (don't block session start)

---

## TASK 6: Mood Check-In System
**Priority:** 🟡 HIGH — Core engagement metric + proof the product works
**Phase:** 1.4
**Estimated Effort:** 2-3 days

### 6.1 — Pre-Session Mood Check-In
**Files:** `frontend/index.html` (modify), `frontend/app.js` (modify)

- [ ] New UI overlay after persona selection, before conversation starts:
  - "आज कैसा महसूस हो रहा है?" (How are you feeling today?)
  - 5 emoji options in a row: 😢 (1) 😟 (2) 😐 (3) 🙂 (4) 😊 (5)
  - Tapping an emoji saves mood and starts the conversation
- [ ] Send mood score to backend: `{ type: "mood_checkin", mood: 3, timing: "pre" }`

### 6.2 — Post-Session Mood Check-In
**Files:** `frontend/app.js` (modify)

- [ ] When user ends session (back button / close):
  - Show mood overlay: "बात करके कैसा लगा?" (How do you feel after talking?)
  - Same 5 emoji options
  - Optional: "क्या बात करके अच्छा लगा?" (Did talking help?) — Yes/No
- [ ] Send post-mood to backend: `{ type: "mood_checkin", mood: 4, timing: "post" }`

### 6.3 — Backend Mood Handling
**Files:** `backend/main.py` (modify), `backend/database.py` (modify)

- [ ] Handle `mood_checkin` WebSocket message type:
  - Save to `mood_logs` table with user_id and timestamp
  - Update `sessions.mood_before` or `sessions.mood_after` based on timing
- [ ] API endpoint (for future dashboard): `GET /api/mood-history?user_id=xxx`

---

## TASK 7: Update Session Management for Database-Backed Sessions
**Priority:** 🟡 MEDIUM — Glues everything together
**Phase:** 1.2 (supports all other tasks)
**Estimated Effort:** 2 days

### 7.1 — Refactor Session Class
**File:** `backend/session.py` (rewrite)

- [ ] Add database fields to `Session`:
  ```python
  class Session:
      db_session_id: UUID        # Database session record ID
      user_id: UUID              # Authenticated user ID (from DB)
      persona: str
      persona_prompt: str
      history: list[dict]        # In-memory for current session (fast LLM access)
      turn_count: int
      mood_before: int | None
      mood_after: int | None
      created_at: datetime
      interrupted: bool
      memory_summary: str | None # Loaded from user_memories table
  ```
- [ ] Update `SessionManager.create()`:
  - Accept authenticated `user_id` (UUID from DB, not anonymous string)
  - Create a database session record
  - Load previous conversation context from DB
  - Load latest memory summary from DB
  - Build enriched system prompt with memory context

### 7.2 — Update WebSocket Handlers
**File:** `backend/main.py` (modify)

- [ ] `start_session`: Create DB session, load memory, set mood_before
- [ ] `end_session`: Save mood_after, mark session ended in DB
- [ ] `audio_data`: Save messages to DB after processing
- [ ] `mood_checkin`: New handler for mood data

---

## TASK 8: Config & Environment Updates
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 1 day

### 8.1 — New Environment Variables
**Files:** `backend/config.py` (modify), `backend/.env.example` (modify)

- [ ] Add new env vars:
  ```
  # Database
  DATABASE_URL=postgresql://user:pass@host:5432/saathi

  # Auth - OTP Provider (MSG91 or Twilio)
  OTP_PROVIDER=msg91
  MSG91_AUTH_KEY=your_msg91_auth_key
  MSG91_TEMPLATE_ID=your_template_id
  # OR
  TWILIO_ACCOUNT_SID=your_twilio_sid
  TWILIO_AUTH_TOKEN=your_twilio_token
  TWILIO_VERIFY_SERVICE_ID=your_verify_sid

  # Auth - Google
  GOOGLE_CLIENT_ID=your_google_client_id

  # Auth - JWT
  JWT_SECRET=your_random_secret_key
  JWT_EXPIRY_DAYS=7
  ```

### 8.2 — Dependencies
**File:** `backend/requirements.txt` (modify)

- [ ] Add new packages:
  ```
  asyncpg>=0.29.0          # PostgreSQL async driver
  python-jose[cryptography]>=3.3.0  # JWT tokens
  passlib>=1.7.4           # Password/token utilities
  httpx>=0.27.0            # Async HTTP client (for OTP API calls)
  alembic>=1.13.0          # Database migrations (optional but recommended)
  ```

---

## Implementation Order (Recommended)

```
Week 1:  TASK 4 (Database)     → Foundation everything depends on
         TASK 8 (Config)       → Env vars & dependencies
         TASK 2 (Personas)     → New therapy-informed personas

Week 2:  TASK 1 (Safety)       → Crisis detection before any user testing
         TASK 7 (Sessions)     → Refactor session management for DB

Week 3:  TASK 3 (Auth)         → Phone OTP + Google sign-in
         TASK 5 (Memory)       → Persistent conversations + summaries

Week 4:  TASK 6 (Mood)         → Pre/post session check-ins
         Integration testing   → End-to-end flow testing
         Bug fixes & polish    → Edge cases, error handling
```

---

## Files Changed Summary

| File | Action | Tasks |
|------|--------|-------|
| `backend/personas.py` | **Rewrite** | 2 |
| `backend/session.py` | **Rewrite** | 5, 7 |
| `backend/main.py` | **Major modify** | 1, 3, 6, 7 |
| `backend/streaming.py` | **Modify** | 1, 5 |
| `backend/config.py` | **Modify** | 2, 8 |
| `backend/.env.example` | **Modify** | 8 |
| `backend/requirements.txt` | **Modify** | 8 |
| `backend/crisis.py` | **New** | 1 |
| `backend/auth.py` | **New** | 3 |
| `backend/database.py` | **New** | 4 |
| `backend/memory.py` | **New** | 5 |
| `backend/schema.sql` | **New** | 4 |
| `frontend/index.html` | **Major modify** | 1, 2, 3, 6 |
| `frontend/app.js` | **Major modify** | 2, 3, 6 |
| `frontend/auth.js` | **New** | 3 |
| `frontend/style.css` | **Modify** | 2, 3, 6 |
| `frontend/websocket.js` | **Modify** | 3 |

---

## Definition of Done

- [ ] User can sign up with phone OTP and return to find their conversations remembered
- [ ] Saathi uses therapy-informed persona (Rogerian / CBT-lite)
- [ ] Crisis keywords trigger helpline display + voice response (tested with keyword list)
- [ ] Legal disclaimers visible on all screens and spoken in first interaction
- [ ] Mood is captured before and after each session
- [ ] Conversations persist across browser refreshes and devices
- [ ] After 5 sessions, Saathi has a memory summary and references past conversations
- [ ] All crisis events are logged to database for review
- [ ] App works on mobile Chrome (Tier 2/3 India primary device)
