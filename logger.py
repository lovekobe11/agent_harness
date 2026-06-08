"""logger.py — Logging & observability.

Dual output: pretty console + structured log file.
"""
import logging
from datetime import datetime
from config import cfg


def setup_logger(name: str = "agent") -> logging.Logger:
    """Create a logger that writes to both console and file."""
    log = logging.getLogger(name)
    if log.handlers:
        return log  # already configured

    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-5s %(message)s", "%H:%M:%S")

    # Console — info and above
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    # File — everything
    fh = logging.FileHandler(cfg.LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)
    return log


logger = setup_logger()
