"""
Saathi Web Sandbox — Configuration.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(override=False)  # Don't override Railway's env vars

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print(f"🔧 Config loaded: OPENAI_API_KEY={'set (' + OPENAI_API_KEY[:8] + '...)' if OPENAI_API_KEY else 'NOT SET'}")
print(f"🔧 Config loaded: GROQ_API_KEY={'set (' + GROQ_API_KEY[:8] + '...)' if GROQ_API_KEY else 'NOT SET (using OpenAI Whisper for STT)'}")

if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY is not set! All STT/LLM/TTS calls will fail.")
    print("   Set it via: export OPENAI_API_KEY=sk-...")
    print("   Or add it to .env file in the backend directory.")
    print("   On Railway: add it in the Variables tab.")

# STT — Use Groq Whisper if available (5-10x faster), fallback to OpenAI
STT_PROVIDER = "groq" if GROQ_API_KEY else "openai"
WHISPER_MODEL = "whisper-large-v3" if STT_PROVIDER == "groq" else "whisper-1"
WHISPER_LANGUAGE = None  # Auto-detect language — handles Hinglish (Hindi+English mix) much better than forcing "hi"

# Whisper prompt to improve recognition of Hinglish and common conversational words
WHISPER_PROMPT = (
    "नमस्ते, हाँ, नहीं, अच्छा, ठीक है, चलो, बताओ, क्या हुआ, "
    "hello, okay, yes, no, please, thank you, sorry, "
    "कैसे हो, क्या चल रहा है, मज़ा आया, बहुत अच्छा, "
    "school, office, meeting, phone, WhatsApp, Instagram, "
    "पापा, मम्मी, भाई, दीदी, यार, बॉस, "
    "stress, tension, problem, happy, sad, angry, "
    "खाना, पानी, चाय, coffee, chai, "
    "actually, basically, seriously, obviously"
)

# LLM
LLM_MODEL = "gpt-4o-mini"  # Faster first-token latency than gpt-4o
LLM_MAX_TOKENS = 300  # Allow longer responses for storytelling while keeping voice-friendly
LLM_TEMPERATURE = 0.8
MAX_CONVERSATION_HISTORY = 30  # 15 turns (user + assistant)

# TTS
TTS_MODEL = "tts-1"
TTS_VOICE = "nova"  # Default voice (overridden per persona)

# Per-persona TTS voices for distinct character feel
TTS_VOICES = {
    "empathy": "nova",      # Warm, gentle — fits the caring friend
    "funny": "echo",        # Energetic, expressive — fits the comedian
    "angry": "onyx",        # Deep, gruff — fits the irritated uncle
    "happy": "shimmer",     # Bright, enthusiastic — fits the cheerleader
    "loving": "fable",      # Soft, wise — fits the loving grandparent
}

# Temp directory for audio files
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
