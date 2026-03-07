"""
TTS Retry Utility
==================
Provides a retry wrapper for gTTS and edge-tts calls that are prone to
network failures, timeouts, or rate-limiting.

Usage:
    from tts.utils.tts_retry import tts_save_with_retry

    # For gTTS:
    from gtts import gTTS
    tts_save_with_retry(
        lambda path: gTTS(text=text, lang='mr').save(path),
        output_path,
        max_retries=2,
        timeout_sec=30,
    )

    # For edge-tts:
    tts_save_with_retry(
        lambda path: asyncio.run(communicate.save(path)),
        output_path,
        max_retries=2,
        timeout_sec=45,
    )
"""
import time
import logging
import socket
from typing import Callable, Optional

logger = logging.getLogger('tts.retry')

# Default timeouts (seconds)
GTTS_TIMEOUT = 30
EDGE_TTS_TIMEOUT = 45

# Retry config
MAX_RETRIES = 2
BACKOFF_BASE = 2  # seconds; doubles each retry (2s, 4s)


def tts_save_with_retry(
    save_fn: Callable[[str], None],
    output_path: str,
    max_retries: int = MAX_RETRIES,
    timeout_sec: int = GTTS_TIMEOUT,
    engine_name: str = 'tts',
) -> None:
    """Call save_fn(output_path) with timeout and retry logic.

    Args:
        save_fn: A callable that takes an output file path and saves audio to it.
            Should raise on failure (network error, timeout, etc.).
        output_path: Path where the audio file should be saved.
        max_retries: Maximum number of retry attempts after first failure.
        timeout_sec: Socket timeout in seconds for this call.
        engine_name: Name of the engine for logging (e.g., 'gTTS', 'edge-tts').

    Raises:
        The last exception if all retries fail.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1 + max_retries):
        try:
            # Set socket timeout for this call
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout_sec)
            try:
                save_fn(output_path)
            finally:
                socket.setdefaulttimeout(old_timeout)

            # Success
            if attempt > 0:
                logger.info("[%s] Succeeded on retry %d", engine_name, attempt)
            return

        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "[%s] Attempt %d/%d failed: %s — retrying in %ds",
                    engine_name, attempt + 1, 1 + max_retries, exc, wait
                )
                time.sleep(wait)
            else:
                logger.error(
                    "[%s] All %d attempts failed. Last error: %s",
                    engine_name, 1 + max_retries, exc
                )

    # All retries exhausted — re-raise last exception
    raise last_exc  # type: ignore[misc]


def check_network(host: str = 'translate.google.com',
                   port: int = 443,
                   timeout: float = 3.0) -> bool:
    """Quick connectivity check — can we reach the TTS API server?

    Returns True if a TCP connection succeeds within timeout.
    Returns False otherwise (no network, DNS failure, firewall, etc.).
    """
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False
