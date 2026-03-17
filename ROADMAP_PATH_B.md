# 🧠 Saathi Path B Roadmap: Hindi Mental Health Companion → First 100 Paying Customers

## The Core Bet

> **600M+ Hindi speakers in Tier 2/3 India have no affordable, stigma-free, voice-first mental wellness support.** Therapy costs ₹1,500-3,000/session, there are 0.3 psychiatrists per 100K people, and most mental health apps are English-only and text-based. Saathi becomes the friend you call when you're stressed, anxious, or lonely — and it speaks your language.

---

## What We Have Today vs. What We Need

| Area | Today | Needed for 100 Paying Customers |
|------|-------|-------------------------------|
| Personas | 5 fun personalities | 1-2 therapy-informed companions |
| User accounts | None (anonymous) | Auth + profiles |
| Memory | Ephemeral (lost on refresh) | Persistent across sessions |
| Mood tracking | None | Per-session + longitudinal |
| Safety | None | Crisis detection + helpline routing |
| Payments | None | Razorpay (UPI-first) |
| Analytics | None | Usage, retention, engagement |
| Distribution | Direct URL | WhatsApp bot + PWA + referrals |
| Database | In-memory dict | PostgreSQL / Supabase |
| Compliance | None | Disclaimers, data privacy, not-a-doctor framing |
| Cost/turn | ~₹1-2.5 ($0.01-0.03) | Need to get under ₹0.50 |

---

## 🗓️ THE ROADMAP: 16 Weeks to 100 Paying Customers

---

## Phase 0: "Reframe" (Week 1-2) — Foundation Decisions

**Goal:** Pivot from toy to product. Set the strategic foundation.

### 0.1 — Positioning & Naming

- **Rename the product for this vertical.** "Saathi" (companion) actually works beautifully for mental health. Keep it.
- **New tagline:** "अपने मन की बात करो। Saathi सुनेगा।" (Share what's on your mind. Saathi will listen.)
- **Critical framing:** Saathi is a **wellness companion**, NOT a therapist. This is not just branding — it's legal protection. Every screen must say: *"Saathi एक AI दोस्त है, therapist नहीं। गंभीर समस्या में professional help लें।"*

### 0.2 — New Persona Design (Replace Current 5)

Replace the 5 fun personas with **2 therapy-informed personas:**

| Persona | Name | Style | Framework |
|---------|------|-------|-----------|
| **Default** | साथी (Saathi) | Warm, patient, gently curious friend. Asks "और बताओ?", validates feelings, never judges. | Rogerian (person-centered) + Active Listening |
| **Guided** | दीदी / भैया (Didi/Bhaiya) | Slightly more structured. Offers breathing exercises, reframing techniques, journaling prompts. | CBT-lite + Motivational Interviewing |

Why only 2: Focus. The "empathy" persona is already 80% there. The "loving" (grandparent) persona is close to the guided one. Don't dilute with comedy/anger for a mental health product.

### 0.3 — Safety Framework Design

**Non-negotiable before any public launch:**

- **Crisis keyword detection** in STT output: suicide-related words (आत्महत्या, मरना चाहता हूँ, जीने का मन नहीं, etc.)
- **Response protocol:** Immediately break character → show helpline numbers → voice message saying "मैं समझ रहा हूँ। अभी Vandrevala Foundation helpline पर call करो: 1860-2662-345"
- **Helplines to integrate:**
  - iCall: 9152987821
  - Vandrevala Foundation: 1860-2662-345
  - AASRA: 9820466726
- **Session-level flags:** If crisis detected, log it (anonymized), prevent further AI interaction until user acknowledges helpline info
- **Legal disclaimer** on every screen and in audio at first interaction

### 0.4 — Deliverables

- [ ] New brand positioning document
- [ ] 2 new persona system prompts (therapy-informed, reviewed by a counselor if possible)
- [ ] Crisis keyword list (Hindi + Hinglish + transliterated)
- [ ] Crisis response flow design
- [ ] Legal disclaimer text (Hindi + English)

---

## Phase 1: "Remember Me" (Week 3-5) — Persistence + Identity

**Goal:** Users can come back and Saathi remembers them. This is THE unlock for retention.

### 1.1 — User Authentication

- **Phone number + OTP** (primary) — this is how Tier 2/3 India logs in. No email.
- Use a service like MSG91 or Twilio Verify for OTP
- **Google Sign-In** as secondary (for urban users)
- Simple onboarding: Name (just first name), age range, what brings you here (dropdown: stress, loneliness, anxiety, just want to talk, other)

### 1.2 — Database (PostgreSQL via Supabase or Railway Postgres)

**Schema (minimal):**

```sql
users:
  id, phone, name, age_range, created_at, last_active

sessions:
  id, user_id, persona, started_at, ended_at, turn_count, mood_before, mood_after

messages:
  id, session_id, role, content, timestamp

mood_logs:
  id, user_id, mood_score (1-5), note, timestamp

crisis_events:
  id, user_id, session_id, trigger_text, timestamp, helpline_shown
```

### 1.3 — Persistent Conversation Memory

- Store all messages in the database
- On new session, load last 10 turns as context for LLM
- Add a **memory summary system**: After every 5 sessions, use GPT to generate a 2-3 line summary of "what Saathi knows about this user" → inject into system prompt
- Example: *"यह user college student है, exam stress से परेशान है, पिछली बार boyfriend से लड़ाई की बात कर रहे थे।"*

### 1.4 — Mood Check-in (Pre/Post Session)

- **Before session:** "आज कैसा महसूस हो रहा है?" with 5 emoji options (😢😟😐🙂😊)
- **After session:** Same question + "क्या बात करके अच्छा लगा?"
- Store in `mood_logs` table
- This is your **core engagement metric** AND the data that proves the product works

### 1.5 — Deliverables

- [ ] Phone OTP auth flow (backend + frontend)
- [ ] PostgreSQL schema + migrations
- [ ] Conversation persistence (save/load)
- [ ] Memory summary generation (GPT-based)
- [ ] Mood check-in UI (pre/post session)

---

## Phase 2: "Make It Healing" (Week 6-8) — Therapeutic Features

**Goal:** Saathi doesn't just chat — it actively helps. This is what differentiates from ChatGPT.

### 2.1 — Guided Exercises (Voice-First)

Build 5-7 guided exercises that Saathi can offer contextually:

1. **4-7-8 Breathing** — Saathi talks you through it in Hindi, with audio cues
2. **Gratitude reflection** — "आज तीन अच्छी बातें बताओ जो हुईं"
3. **Thought reframing (CBT-lite)** — "तुमने कहा 'मैं कुछ नहीं कर सकता।' क्या ऐसा कोई time याद है जब तुमने कुछ मुश्किल किया?"
4. **Body scan** — Quick 2-minute guided relaxation
5. **Journaling prompt** — "आज एक चीज़ जो तुम्हें परेशान कर रही है, उसके बारे में बोलो"
6. **Sleep story** — A calming Hindi story for bedtime (this is a retention MAGNET)
7. **Anger release** — "चलो, जो गुस्सा है वो बोल डालो। मैं सुन रहा हूँ।"

**Implementation:** These are specialized system prompt injections + pre-recorded TTS segments for the structured parts (breathing counts, etc.). The LLM handles the conversational wrapper.

### 2.2 — Contextual Intelligence

Enhance the LLM prompts to:

- **Detect themes** from conversation: stress, loneliness, relationship issues, work pressure, family conflict, academic pressure, sleep issues
- **Suggest exercises** based on theme: If user talks about anxiety → offer breathing exercise. If loneliness → ask about their day, be extra warm.
- **Track recurring themes** across sessions using the memory summary

### 2.3 — "How Are You Doing?" Weekly Summary

- Every Sunday, generate a voice message or text summary:
  - *"इस हफ्ते तुमने 4 बार बात की। तुम्हारा mood mostly 😟 से 🙂 गया। बहुत अच्छा! अगले हफ्ते भी बात करते हैं।"*
- Send via WhatsApp or push notification (see Phase 3)

### 2.4 — Deliverables

- [ ] 5-7 guided exercise scripts (Hindi)
- [ ] Exercise delivery system (system prompt injection + pre-recorded audio segments)
- [ ] Theme detection from conversations
- [ ] Contextual exercise suggestions
- [ ] Weekly summary generation

---

## Phase 3: "Pay & Stay" (Week 9-11) — Monetization + Retention

**Goal:** Free tier hooks them, paid tier keeps them. Revenue starts.

### 3.1 — Freemium Model

| | Free (मुफ़्त) | Saathi Plus (₹149/month) |
|--|-------------|------------------------|
| Sessions/day | 2 | Unlimited |
| Session length | 5 minutes | 30 minutes |
| Mood tracking | Basic (emoji only) | Detailed + weekly reports |
| Guided exercises | 2 (breathing + gratitude) | All 7 |
| Memory | Last session only | Full history + memory summary |
| Sleep stories | ❌ | ✅ Nightly stories |
| Priority response | ❌ | ✅ Faster (skip queue) |

**Why ₹149/month (~$1.80):**

- Below the "chai money" threshold (₹5/day)
- UPI makes ₹149 feel like nothing
- Competitors: Wysa charges ₹2,499/year ($30) for premium. We're undercutting hard to build volume.
- At 100 users × ₹149 = ₹14,900/month revenue (~$180/month). Not life-changing, but proves PMF.

### 3.2 — Payment Integration (Razorpay)

- **UPI first** — this is how 80% of Tier 2/3 India pays
- Razorpay Subscriptions API for recurring billing
- Show price as "₹5/day" not "₹149/month" (psychological pricing)
- **7-day free trial** of Plus after 3rd free session (the hook: they've already invested emotionally)

### 3.3 — Retention Mechanics

- **Streak counter:** "तुमने लगातार 5 दिन बात की! 🔥" (gamification works in India — see CRED, Duolingo)
- **Daily check-in reminder:** WhatsApp message at 9 PM: "आज कैसा दिन रहा? बात करोगे? 🤗" with a link
- **Mood garden (visual):** Each session plants a flower. Your garden grows. Simple but effective.
- **Milestone celebrations:** "10वीं बातचीत! तुम बहुत brave हो।"

### 3.4 — Deliverables

- [ ] Razorpay subscription integration (UPI + card)
- [ ] Free/paid tier gating logic
- [ ] Paywall UI (in Hindi, empathetic tone, not aggressive)
- [ ] Streak tracking + UI
- [ ] Daily reminder system (WhatsApp API or push notifications)
- [ ] Trial flow (auto-trigger after 3rd session)

---

## Phase 4: "Reach Them" (Week 12-14) — Distribution

**Goal:** Get Saathi in front of the right people. Organic-first, then paid.

### 4.1 — WhatsApp Integration (THE channel for Tier 2/3 India)

- **WhatsApp Business API** (via Twilio or Gupshup)
- User sends "Hi" to Saathi's WhatsApp number → gets a link to open the web app
- Daily check-in messages via WhatsApp (much higher open rate than email or push)
- **Voice notes on WhatsApp?** Stretch goal — accept voice notes directly on WhatsApp, process them, reply with voice note. This would be HUGE for adoption.

### 4.2 — Content Marketing (Hindi-First)

**Instagram Reels / YouTube Shorts (MOST IMPORTANT CHANNEL):**

- "3 signs कि तुम्हें mental health break चाहिए" — Hindi, relatable, 30-second reel
- "मैंने AI से अपने दिल की बात कही" — user testimonial (even if staged initially)
- "Exam stress? यह breathing exercise try करो" — value-first content with Saathi branding
- Target: 3 reels/week, Hindi captions, relatable Tier 2/3 scenarios (exam pressure, family fights, job stress, loneliness in a new city)

**YouTube (long-form):**

- "मैंने 30 दिन AI therapist से बात की — क्या हुआ?" — personal experiment video
- Partner with Hindi mental health YouTubers (The Vocal, Fit Tuber's mental health segments)

### 4.3 — Community Seeding

- **Reddit:** r/india, r/indianpeoplequora, r/TwoXIndia — share genuinely helpful posts about mental health, mention Saathi naturally
- **College WhatsApp groups:** Partner with 5-10 college mental health cells/NSS chapters. Offer Saathi Plus free for their students.
- **HR wellness programs:** Pitch to 3-5 Indian startups/BPOs as an employee wellness add-on (B2B2C — company pays, employees use)

### 4.4 — Referral Program

- "अपने दोस्त को भी Saathi से मिलवाओ" — share link via WhatsApp
- Both referrer and referred get 7 days of Saathi Plus free
- **WhatsApp share button** with pre-written message: "यार, यह app try कर — हिंदी में बात कर सकते हो अपने मन की। मुझे अच्छा लगा: [link]"

### 4.5 — Deliverables

- [ ] WhatsApp Business API integration (check-in messages + deep links)
- [ ] Landing page redesign (mental health positioning, Hindi-first, testimonials)
- [ ] Content calendar: 12 reels scripted for first month
- [ ] Referral system (generate/track referral links, reward logic)
- [ ] College outreach list (10 colleges) + pitch deck

---

## Phase 5: "Prove It" (Week 15-16) — Measure, Iterate, Hit 100

**Goal:** Instrument everything. Find what's working. Double down.

### 5.1 — Analytics Dashboard

Track these religiously:

| Metric | Tool | Target |
|--------|------|--------|
| Daily Active Users (DAU) | PostHog/Mixpanel | 300+ (to get 100 paying) |
| D1 / D7 / D30 retention | PostHog | 40% / 20% / 10% |
| Avg session length | Custom | >5 minutes |
| Sessions/week (active user) | Custom | >3 |
| Free → Trial conversion | Custom | >30% |
| Trial → Paid conversion | Custom | >15% |
| Mood improvement (pre vs post) | Custom | >60% report feeling better |
| Crisis events | Custom | Track & review every one |
| Cost per user/month | Custom | <₹40 ($0.50) |
| CAC (customer acquisition cost) | Custom | <₹200 ($2.50) |
| LTV (lifetime value) | Custom | >₹600 (4+ months retention) |

### 5.2 — Cost Optimization (Critical at Scale)

Current stack costs ~₹1-2.5 per turn. At 100 users × 5 sessions/day × 10 turns = **5,000 turns/day = ₹5,000-12,500/day.** That's ₹1.5-3.75 lakh/month in API costs against ₹14,900/month revenue. **This doesn't work.**

**Cost reduction plan:**

| Action | Savings | Effort |
|--------|---------|--------|
| Groq Whisper for STT (already supported!) | ~60% on STT | Low ✅ |
| Switch to GPT-4o-mini (already done!) | ~80% vs GPT-4o | Done ✅ |
| Cache common TTS phrases (greetings, fillers, exercise instructions) | ~30% on TTS | Medium |
| Use Deepgram or local Whisper for STT | ~70% on STT | Medium |
| Explore open-source Hindi TTS (Coqui/VITS) | ~90% on TTS | High |
| Shorter responses (2-3 sentences max for voice) | ~40% on LLM | Low ✅ |
| Rate limit free tier aggressively | N/A | Low |

**Target unit economics at 100 users:**

- Revenue: ₹14,900/month
- API costs (optimized): ₹3,000-5,000/month
- Infrastructure (Railway): ₹1,000/month
- WhatsApp API: ₹500/month
- **Gross profit: ₹8,400-10,400/month (~55-70% margin)**

### 5.3 — Feedback Loop

- After every 5th session: "Saathi से बात करके कैसा लगता है? कुछ और चाहिए?" (in-app voice feedback)
- Monthly user interviews: Call 5 active users, ask what's working, what's missing
- Track the #1 reason people cancel (if they do)

### 5.4 — Deliverables

- [ ] Analytics integration (PostHog or Mixpanel — free tier is enough)
- [ ] Cost monitoring dashboard (track API spend per user)
- [ ] User feedback collection system
- [ ] A/B test framework for paywall timing and pricing

---

## 📅 Summary Timeline

```
Week 1-2:   REFRAME     → New positioning, therapy-informed personas, safety framework
Week 3-5:   REMEMBER ME → Auth, database, persistent memory, mood check-ins
Week 6-8:   HEAL        → Guided exercises, contextual intelligence, weekly summaries
Week 9-11:  MONETIZE    → Razorpay, freemium tiers, retention mechanics, streaks
Week 12-14: DISTRIBUTE  → WhatsApp, Instagram reels, college outreach, referrals
Week 15-16: PROVE IT    → Analytics, cost optimization, feedback loops, iterate
```

---

## 🚀 The 100-Customer Math

```
Week 12-14: Launch publicly
  → Instagram reels reach ~50K views (Hindi mental health content performs well)
  → 2% click-through = 1,000 visitors
  → 30% sign up (free) = 300 users
  → 40% come back D7 = 120 active users
  → 30% hit trial trigger = 36 trials
  → 50% convert to paid = 18 paying customers

  → WhatsApp referrals: 18 users × 2 referrals each = 36 new users → 5 more paying
  → College partnerships (5 colleges × 50 students) = 250 users → 15 paying

Week 14: ~38 paying customers

Week 15-16: Double down on what's working
  → More reels (now with real testimonials)
  → More college partnerships
  → Optimize conversion funnel based on data
  → HR/B2B2C outreach starts bearing fruit

Week 16: 80-120 paying customers ✅
```

---

## ⚠️ Top Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| User in crisis gets bad AI advice | **Critical** | Crisis detection system (Phase 0), mandatory helpline routing, "not a therapist" disclaimers everywhere |
| API costs blow up before revenue | High | Aggressive cost optimization (Phase 5), hard rate limits on free tier, Groq STT |
| Low willingness to pay at ₹149 | High | Test ₹99 and ₹49 tiers. Consider ad-supported free tier. B2B2C (companies pay for employees) |
| Regulatory action (India's Digital Health Act) | Medium | Frame as wellness, not therapy. No diagnosis, no prescriptions. Consult a health-tech lawyer (₹10-15K one-time) |
| Hindi TTS quality sounds robotic | Medium | OpenAI's TTS is actually good for Hindi. Test with real users. |
| Users prefer typing over voice | Medium | Add text input option as fallback. But voice-first is the differentiator — don't lose it. |

---

## 🏗️ Technical Architecture (Target State)

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (PWA)                    │
│  Vanilla JS + Web Audio API + VAD + WebSocket       │
│  Mood check-in UI, streak/garden visuals, paywall   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Auth (OTP)  │  │ WhatsApp Bot │  │ Razorpay   │ │
│  │ MSG91/Twilio│  │ Gupshup API  │  │ Subs API   │ │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                │                │        │
├─────────┴────────────────┴────────────────┴────────┤
│              FastAPI Backend (Python)               │
│  WebSocket handler, streaming pipeline,             │
│  crisis detection, session management,              │
│  exercise engine, memory summarizer                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Groq     │  │ OpenAI   │  │ OpenAI TTS       │  │
│  │ Whisper  │  │ GPT-4o-  │  │ (nova/shimmer)   │  │
│  │ (STT)    │  │ mini     │  │                  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
├─────────────────────────────────────────────────────┤
│              PostgreSQL (Supabase/Railway)           │
│  users, sessions, messages, mood_logs,              │
│  crisis_events, subscriptions, referrals            │
├─────────────────────────────────────────────────────┤
│              Analytics (PostHog)                     │
│  DAU, retention, conversion, session metrics        │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Master Checklist (All Deliverables)

### Phase 0 — Reframe (Week 1-2)
- [ ] New brand positioning document
- [ ] 2 new persona system prompts (therapy-informed)
- [ ] Crisis keyword list (Hindi + Hinglish + transliterated)
- [ ] Crisis response flow design
- [ ] Legal disclaimer text (Hindi + English)

### Phase 1 — Remember Me (Week 3-5)
- [ ] Phone OTP auth flow (backend + frontend)
- [ ] PostgreSQL schema + migrations
- [ ] Conversation persistence (save/load)
- [ ] Memory summary generation (GPT-based)
- [ ] Mood check-in UI (pre/post session)

### Phase 2 — Make It Healing (Week 6-8)
- [ ] 5-7 guided exercise scripts (Hindi)
- [ ] Exercise delivery system (system prompt injection + pre-recorded audio)
- [ ] Theme detection from conversations
- [ ] Contextual exercise suggestions
- [ ] Weekly summary generation

### Phase 3 — Pay & Stay (Week 9-11)
- [ ] Razorpay subscription integration (UPI + card)
- [ ] Free/paid tier gating logic
- [ ] Paywall UI (in Hindi, empathetic tone)
- [ ] Streak tracking + UI
- [ ] Daily reminder system (WhatsApp API or push)
- [ ] Trial flow (auto-trigger after 3rd session)

### Phase 4 — Reach Them (Week 12-14)
- [ ] WhatsApp Business API integration
- [ ] Landing page redesign (mental health positioning)
- [ ] Content calendar: 12 reels scripted
- [ ] Referral system (generate/track links, reward logic)
- [ ] College outreach list (10 colleges) + pitch deck

### Phase 5 — Prove It (Week 15-16)
- [ ] Analytics integration (PostHog/Mixpanel)
- [ ] Cost monitoring dashboard
- [ ] User feedback collection system
- [ ] A/B test framework for paywall timing and pricing
