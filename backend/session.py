"""
Saathi Web Sandbox — Session Manager.
Manages per-connection sessions with conversation history and persona state.
"""

from datetime import datetime
from personas import PERSONA_PROMPTS
from config import MAX_CONVERSATION_HISTORY


class Session:
    """A single user's conversation session."""

    def __init__(self, user_id: str, persona: str):
        self.user_id = user_id
        self.persona = persona
        self.persona_prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["empathy"])
        self.history: list[dict] = []
        self.turn_count = 0
        self.created_at = datetime.now()
        self.interrupted = False  # Set to True when user interrupts AI speech

    def add_turn(self, user_text: str, assistant_text: str):
        """Add a conversation turn to history."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
        self.turn_count += 1

        # Trim history to keep last N messages
        if len(self.history) > MAX_CONVERSATION_HISTORY:
            self.history = self.history[-MAX_CONVERSATION_HISTORY:]

    def reset(self, new_persona: str):
        """Reset session with a new persona."""
        self.persona = new_persona
        self.persona_prompt = PERSONA_PROMPTS.get(new_persona, PERSONA_PROMPTS["empathy"])
        self.history = []
        self.turn_count = 0
        self.interrupted = False

    @property
    def duration_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class SessionManager:
    """Manages all active sessions."""

    def __init__(self):
        self._sessions: dict = {}  # keyed by websocket id

    def create(self, ws_id: str, user_id: str, persona: str) -> Session:
        session = Session(user_id, persona)
        self._sessions[ws_id] = session
        return session

    def get(self, ws_id: str) -> Session | None:
        return self._sessions.get(ws_id)

    def remove(self, ws_id: str):
        self._sessions.pop(ws_id, None)
