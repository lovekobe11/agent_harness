"""session.py — Session management.

Tracks conversation history per session, supports save/load.
"""
from __future__ import annotations
import json, uuid
from pathlib import Path
from config import cfg
from logger import logger
from datetime import datetime

class Session:
    """One conversation session with message history."""

    def __init__(self, session_id: str | None = None):
        self.id = session_id or uuid.uuid4().hex[:8]
        self.messages: list[dict] = []       # [{role, content}, ...]
        self.created_at = datetime.now().isoformat()
        Path(cfg.SESSION_DIR).mkdir(parents=True, exist_ok=True)

    # --- message handling ---

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def history(self, last_n: int = 20) -> list[dict]:
        """Return recent messages (for API calls)."""
        return self.messages[-last_n:]

    # --- persistence ---

    def save(self) -> str:
        path = Path(cfg.SESSION_DIR) / f"{self.id}.json"
        data = {"id": self.id, "created_at": self.created_at, "messages": self.messages}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.debug("Session saved: %s", self.id)
        return self.id

    @classmethod
    def load(cls, session_id: str) -> "Session":
        path = Path(cfg.SESSION_DIR) / f"{session_id}.json"
        data = json.loads(path.read_text())
        s = cls(session_id=data["id"])
        s.messages = data["messages"]
        s.created_at = data["created_at"]
        return s

    @staticmethod
    def list_sessions() -> list[str]:
        d = Path(cfg.SESSION_DIR)
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.json"))
