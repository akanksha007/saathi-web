# Saathi (साथी) — Hindi Conversational AI

A voice-based Hindi conversational AI with multiple personas. Speak Hindi, hear Hindi — in your browser.

## Quick Start (Local)

```bash
cd backend
cp .env.example .env   # Add your API keys
pip install -r requirements.txt
python main.py
```

Open `http://localhost:8000`

## Deploy to Railway

See deployment instructions in `Phase3_Technical_Implementation.md` → Section 8.

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS + Silero VAD
- **Backend:** FastAPI (Python) + WebSocket
- **STT:** OpenAI Whisper API
- **LLM:** OpenAI GPT-4o
- **TTS:** OpenAI TTS-1 (nova voice)
