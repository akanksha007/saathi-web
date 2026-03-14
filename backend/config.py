"""
Saathi Web Sandbox — Configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# STT
WHISPER_MODEL = "whisper-1"
WHISPER_LANGUAGE = "hi"

# LLM
LLM_MODEL = "gpt-4o"
LLM_MAX_TOKENS = 500
LLM_TEMPERATURE = 0.8
MAX_CONVERSATION_HISTORY = 30  # 15 turns (user + assistant)

# TTS
TTS_MODEL = "tts-1"
TTS_VOICE = "nova"

# Temp directory for audio files
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
