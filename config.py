"""config.py — Configuration management.

Loads settings from .env file. All knobs live here in one place.
"""
import os
from pathlib import Path

# Auto-load .env (checks project root first, then same directory)
_here = Path(__file__).resolve().parent
for _candidate in [_here.parent / ".env", _here / ".env"]:
    if _candidate.exists():
        for line in _candidate.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        break


class Config:
    """Central configuration — change values here or via environment variables."""

    API_KEY: str = os.getenv("DASHSCOPE_API_KEY")
    BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL: str = "qwen3.6-flash-2026-04-16" ##"qwen3.7-plus" 
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2048
    MAX_LOOPS: int = 5          # max tool-call rounds per user turn
    MEMORY_FILE: str = str(Path(__file__).parent / "memory_store.json")
    LOG_FILE: str = str(Path(__file__).parent / "agent.log")
    SESSION_DIR: str = str(Path(__file__).parent / "sessions")


cfg = Config()
