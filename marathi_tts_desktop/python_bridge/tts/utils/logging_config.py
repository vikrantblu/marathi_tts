"""
tts.utils.logging_config — standalone version (no Django dependency).

Provides setup_logging() and get_logger() for use in the desktop bridge
scripts. The log directory is resolved from the MARATHI_TTS_PROJECT_ROOT
environment variable (falls back to the user home directory).
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Resolved at import time so all callers share the same root.
_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    os.path.expanduser("~"),
)

_SETUP_COMPLETE = False


def setup_logging(force: bool = False) -> dict:
    """Configure a rotating-file + console logging setup.

    Safe to call multiple times — does nothing after the first call unless
    *force* is True.  Does NOT require Django to be configured.
    """
    global _SETUP_COMPLETE
    if _SETUP_COMPLETE and not force:
        return {}
    try:
        log_dir = os.path.join(_PROJECT_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        main_log = os.path.join(log_dir, "tts.log")

        fmt = logging.Formatter(
            "[%(asctime)s] [PID:%(process)d] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = RotatingFileHandler(
            main_log, maxBytes=10 * 1024 * 1024, backupCount=5,
            encoding="utf-8", delay=True,
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        ch.setLevel(logging.INFO)

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.DEBUG)
        root.addHandler(fh)
        root.addHandler(ch)

        _SETUP_COMPLETE = True
    except Exception as exc:
        print(f"[logging_config] setup_logging failed: {exc}")
    return {}


def get_logger(name: str) -> logging.Logger:
    """Return a logger with both file and console handlers.

    Idempotent — attaches handlers only once per logger name.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "[%(asctime)s] [PID:%(process)d] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Optional rotating file handler (skip silently on I/O errors)
    try:
        log_dir = os.path.join(_PROJECT_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(log_dir, f"{name}.log"),
            maxBytes=5 * 1024 * 1024, backupCount=3,
            encoding="utf-8", delay=True,
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    except Exception:
        pass

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger
