"""
Saathi — Session Manager.
Manages per-connection sessions with conversation history, persona state,
database persistence, and memory context.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from personas import PERSONA_PROMPTS, MEMORY_CONTEXT_TEMPLATE
from config import MAX_CONVERSATION_HISTORY


class Session:
    """A single user's conversation session."""

    def __init__(self, user_id: str, persona: str):
        self.user_id = user_id                     # Anonymous or authenticated user identifier
        self.user_id_uuid: Optional[UUID] = None   # Database user UUID (set after auth)
        self.db_session_id: Optional[UUID] = None  # Database session record UUID
        self.persona = persona
        self.persona_prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["saathi"])
        self.history: list[dict] = []
        self.turn_count = 0
        self.mood_before: Optional[int] = None
        self.mood_after: Optional[int] = None
        self.memory_summary: Optional[str] = None
        self.created_at = datetime.now()
        self.interrupted = False

    def set_db_context(self, user_id_uuid: UUID, db_session_id: UUID):
        """Set database-backed identifiers after session creation in DB."""
        self.user_id_uuid = user_id_uuid
        self.db_session_id = db_session_id

    def set_memory(self, memory_summary: str):
        """
        Inject memory context from previous sessions into the system prompt.
        This makes Saathi 'remember' the user across sessions.
        """
        self.memory_summary = memory_summary
        if memory_summary:
            memory_block = MEMORY_CONTEXT_TEMPLATE.format(memory_summary=memory_summary)
            # Prepend memory context to persona prompt
            self.persona_prompt = self.persona_prompt + "\n" + memory_block

    def load_history(self, messages: list[dict]):
        """
        Load previous conversation messages (from DB) into session history.
        Messages should be dicts with 'role' and 'content' keys.
        """
        for msg in messages:
            self.history.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        # Trim if too many
        if len(self.history) > MAX_CONVERSATION_HISTORY:
            self.history = self.history[-MAX_CONVERSATION_HISTORY:]

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
        self.persona_prompt = PERSONA_PROMPTS.get(new_persona, PERSONA_PROMPTS["saathi"])
        self.history = []
        self.turn_count = 0
        self.mood_before = None
        self.mood_after = None
        self.memory_summary = None
        self.db_session_id = None
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
