"""
TTS Error Codes
================
Structured error codes for TTS bridge responses. Allows Kotlin/JavaFX callers
to match on codes instead of parsing free-text error messages.

Usage:
    from tts.constants.error_codes import ERR_EMPTY_TEXT, ERR_NO_NETWORK

    return {"success": False, "error": "...", "error_code": ERR_EMPTY_TEXT}
"""

# ── Validation errors ─────────────────────────────────────────────────────
ERR_EMPTY_TEXT = "ERR_EMPTY_TEXT"           # Input text is empty or whitespace
ERR_INVALID_LANG = "ERR_INVALID_LANG"      # Unsupported language code

# ── Network errors ────────────────────────────────────────────────────────
ERR_NO_NETWORK = "ERR_NO_NETWORK"          # No internet connectivity
ERR_TTS_TIMEOUT = "ERR_TTS_TIMEOUT"        # gTTS/edge-tts HTTP request timed out
ERR_TTS_RATE_LIMIT = "ERR_TTS_RATE_LIMIT"  # API rate limit hit (429)

# ── Engine errors ─────────────────────────────────────────────────────────
ERR_ENGINE_UNAVAILABLE = "ERR_ENGINE_UNAVAILABLE"  # No TTS engine could be loaded
ERR_ALL_ENGINES_FAILED = "ERR_ALL_ENGINES_FAILED"  # All fallback stages exhausted
ERR_EDGE_TTS_FAILED = "ERR_EDGE_TTS_FAILED"       # edge-tts specific failure
ERR_GTTS_FAILED = "ERR_GTTS_FAILED"               # gTTS specific failure

# ── Audio processing errors ───────────────────────────────────────────────
ERR_AUDIO_PROCESSING = "ERR_AUDIO_PROCESSING"  # pydub / ffmpeg post-processing failed
ERR_FILE_IO = "ERR_FILE_IO"                    # Could not read/write audio file

# ── Convenience lookup: human-readable default messages ───────────────────
DEFAULT_MESSAGES = {
    ERR_EMPTY_TEXT: "Input text is empty.",
    ERR_INVALID_LANG: "Unsupported language code.",
    ERR_NO_NETWORK: "No internet connection. Please check your network and try again.",
    ERR_TTS_TIMEOUT: "TTS request timed out. Please try again.",
    ERR_TTS_RATE_LIMIT: "TTS service rate limit reached. Please wait and try again.",
    ERR_ENGINE_UNAVAILABLE: "No TTS engine available.",
    ERR_ALL_ENGINES_FAILED: "All TTS engines failed. Please try again later.",
    ERR_EDGE_TTS_FAILED: "Microsoft Edge TTS failed.",
    ERR_GTTS_FAILED: "Google TTS failed.",
    ERR_AUDIO_PROCESSING: "Audio processing error.",
    ERR_FILE_IO: "File read/write error.",
}
