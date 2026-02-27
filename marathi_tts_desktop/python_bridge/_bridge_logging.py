#!/usr/bin/env python3
"""
Shared logging setup for all Marathi TTS bridge scripts.

Creates a logger that writes to:
  1. stderr  — captured by Java's PythonBridge and shown in the app console
  2. rotating file — BRIDGE_DIR/logs/<name>.log  (persists between runs)

Usage:
    from _bridge_logging import get_logger
    log = get_logger(__name__)      # or get_logger("tts_bridge")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_INITIALIZED: set = set()

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _log_dir() -> str:
    """Return (and create) the logs directory next to this file."""
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "logs")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = os.path.join(os.path.expanduser("~"), ".marathi_tts_logs")
        os.makedirs(d, exist_ok=True)
    return d


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Return a configured logger for *name*.

    Creates handlers only once per logger name to avoid duplicate lines
    when a bridge module is imported multiple times (e.g. Chaquopy reuse).
    """
    logger = logging.getLogger(name)
    if name in _INITIALIZED:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FMT)

    # ── stderr handler (always; Java captures this as warnings) ───────────
    stderr_h = logging.StreamHandler(sys.stderr)
    stderr_h.setLevel(logging.DEBUG)
    stderr_h.setFormatter(fmt)
    logger.addHandler(stderr_h)

    # ── rotating file handler ──────────────────────────────────────────────
    try:
        log_file = os.path.join(_log_dir(), f"{name.replace('.', '_')}.log")
        file_h = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        )
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(fmt)
        logger.addHandler(file_h)
    except Exception:
        pass  # If we can't write logs, don't crash the bridge

    logger.propagate = False
    _INITIALIZED.add(name)
    return logger
