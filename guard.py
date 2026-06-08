"""guard.py — Safety guard.

Filters dangerous content before it reaches the model or the user.
"""
from __future__ import annotations
import re
from logger import logger
# Simple block-list (extend as needed)
BLOCKED_PATTERNS = [
    r"(?i)\b(hack|exploit|malware|phishing|ddos)\b",
    r"(?i)(DROP\s+TABLE|DELETE\s+FROM|rm\s+-rf)",
]
# Sensitive data patterns
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),       # US SSN
    (r"\b\d{16,19}\b", "[CARD_REDACTED]"),                # credit card
]

def is_safe(text: str) -> tuple[bool, str]:
    """Check if input text is safe to process. Returns (safe, reason)."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            logger.warning("Guard blocked input: %s", text[:60])
            return False, "Input contains potentially harmful content."
    return True, ""


def redact_pii(text: str) -> str:
    """Replace sensitive data in output with placeholders."""
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
