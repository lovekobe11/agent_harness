"""memory.py — Long-term memory.

JSON-file key-value store with timestamps and auto-trim (1MB limit).
"""
from __future__ import annotations
import json, time
from pathlib import Path
from config import cfg
from logger import logger

MAX_SIZE = 1 * 1024 * 1024  # 1 MB


class Memory:
    """Persistent key-value memory backed by a JSON file."""

    def __init__(self):
        self._path = Path(cfg.MEMORY_FILE)
        self._data: dict = {}
        self._meta: dict = {}  # {key: timestamp} for trim ordering
        self._load()

    # --- public API ---
    def remember(self, key: str, value: str) -> None:
        """Store a fact for later recall."""
        self._data[key] = value
        self._meta[key] = time.time()
        self._save()
        logger.info("Memory stored: %s", key)

    def recall(self, key: str) -> str | None:
        """Retrieve a stored fact."""
        return self._data.get(key)

    def forget(self, key: str) -> None:
        """Delete a fact."""
        self._data.pop(key, None)
        self._meta.pop(key, None)
        self._save()

    def summary(self) -> str:
        """Return all memories as readable text."""
        if not self._data:
            return "(no memories)"
        return "\n".join(f"- {k}: {v}" for k, v in self._data.items())

    # --- internals ---
    def _load(self):
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            if isinstance(raw, dict) and "_meta" in raw:
                self._data = raw.get("memories", {})
                self._meta = raw.get("_meta", {})
            else:
                self._data = raw  # legacy plain-dict format
                self._meta = {k: 0 for k in self._data}

    def _save(self):
        self._trim()
        payload = {"memories": self._data, "_meta": self._meta}
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    def _trim(self):
        """Remove oldest memories if file exceeds MAX_SIZE."""
        raw = json.dumps({"memories": self._data, "_meta": self._meta}, ensure_ascii=False)
        if len(raw.encode("utf-8")) <= MAX_SIZE:
            return
        # Sort keys by timestamp (oldest first) and remove 20% at a time
        sorted_keys = sorted(self._meta, key=lambda k: self._meta.get(k, 0))
        remove_count = max(1, len(sorted_keys) // 5)
        for k in sorted_keys[:remove_count]:
            self._data.pop(k, None)
            self._meta.pop(k, None)
        logger.info("Memory trimmed: removed %d oldest entries", remove_count)
