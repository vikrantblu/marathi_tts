#!/usr/bin/env python3
"""
TTS Bridge - Marathi Text-to-Speech
====================================
Standalone CLI bridge called by the JavaFX desktop app and Chaquopy (Android).

Usage (CLI / desktop):
    python tts_bridge.py --text "मराठी मजकूर" [--speed 1.0] [--pitch 1.0]
                         [--volume 1.0] [--output /path/to/out.mp3]
                         [--emotion happy] [--verse]

Returns: JSON to stdout
    { success, audio_path }          on success
    { success:false, error, stage }  on failure

Engine priority:
  1. gTTS + pydub speed/pitch post-processing  (primary standalone)
  2. gTTS bare fallback (no pydub)
"""

import sys
import os
import json
import argparse
import tempfile
import traceback
import time
import socket

# Cap individual socket ops to 30s so gTTS fails fast on bad networks
socket.setdefaulttimeout(30)

# -- Logging setup ----------------------------------------------------------
_BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BRIDGE_DIR)
try:
    from _bridge_logging import get_logger
except ImportError:
    import logging
    def get_logger(n, **kw):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                            format="[%(asctime)s] [%(levelname)s] %(message)s")
        return logging.getLogger(n)

log = get_logger("tts_bridge")

# -- Path setup -------------------------------------------------------------
_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

_OUTPUT_DIR = os.path.join(_BRIDGE_DIR, "output")
os.makedirs(_OUTPUT_DIR, exist_ok=True)

log.info("TTS Bridge initialised | bridge_dir=%s | output_dir=%s",
         _BRIDGE_DIR, _OUTPUT_DIR)

# -- Phonetic engine --------------------------------------------------------
try:
    from tts.utils.phonetic.marathi_phonetics import (
        apply_sanskrit_phonetics,
        apply_marathi_phonetics,
        preprocess_stotra_text as _phonetic_stotra,
    )
    log.info("Phonetic engine (marathi_phonetics) loaded OK")
except ImportError as _e:
    log.warning("marathi_phonetics not available (%s) — using fallback", _e)
    def apply_sanskrit_phonetics(t): return t
    def apply_marathi_phonetics(t): return t
    _phonetic_stotra = None


# ---------------------------------------------------------------------------
# G2P Engine (lazy singleton)
# ---------------------------------------------------------------------------
_g2p_engine = None

def _get_g2p():
    """Lazy-load the G2P engine. Returns None if unavailable."""
    global _g2p_engine
    if _g2p_engine is not None:
        return _g2p_engine
    try:
        from tts.utils.phonetic.g2p_engine import MarathiG2PEngine
        _g2p_engine = MarathiG2PEngine()
        log.info("G2P engine loaded OK")
        return _g2p_engine
    except Exception as exc:
        log.warning("G2P engine not available: %s", exc)
        return None


def _apply_g2p(text: str) -> str:
    """Run text through G2P engine; return original on failure."""
    g2p = _get_g2p()
    if g2p is None:
        return text
    try:
        result = g2p.process(text)
        log.debug("G2P processed | %d -> %d chars", len(text), len(result))
        return result
    except Exception as exc:
        log.warning("G2P processing failed: %s", exc)
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_pitch_speed(src: str, speed: float, pitch: float, volume: float, dst: str) -> str:
    """Apply speed/pitch/volume adjustments via pydub. Returns dst path."""
    try:
        from pydub import AudioSegment  # type: ignore
        import math
        log.debug("pydub effects | speed=%.2f pitch=%.2f volume=%.2f", speed, pitch, volume)
        audio = AudioSegment.from_mp3(src)

        if abs(speed - 1.0) > 0.02:
            audio = audio._spawn(audio.raw_data,
                                 overrides={"frame_rate": int(audio.frame_rate * speed)})
            audio = audio.set_frame_rate(22050)

        if abs(pitch - 1.0) > 0.02:
            audio = audio._spawn(audio.raw_data,
                                 overrides={"frame_rate": int(audio.frame_rate * pitch)})
            audio = audio.set_frame_rate(22050)

        if abs(volume - 1.0) > 0.02:
            audio = audio + (20 * math.log10(max(volume, 0.01)))

        audio.export(dst, format="mp3")
        log.debug("pydub done -> %s (%.1fs)", dst, len(audio) / 1000)
        return dst
    except ImportError:
        log.warning("pydub not installed - skipping audio effects")
    except Exception as exc:
        log.error("pydub failed: %s", exc)

    import shutil
    if src != dst:
        shutil.copy(src, dst)
    return dst


def _normalize_marathi(text: str) -> str:
    """Normalize via web-app utility; return original text on failure."""
    try:
        from tts.utils.text.text_normalizer import MarathiTextNormalizer  # type: ignore
        result = MarathiTextNormalizer().normalize_text(text)
        log.debug("Text normalized | %d -> %d chars", len(text), len(result))
        return result
    except Exception as exc:
        log.warning("Text normalization unavailable (%s) - using raw text", exc)
        return text


def _preprocess_stotra_text(text: str) -> str:
    """Apply pronunciation and pause rules for stotra/shloka text.

    If the full phonetic module is available, delegates to it.
    Otherwise falls back to inline rules.

    Pronunciation rules (via module):
      - Terminal halant expansion (म् → म)
      - Visarga context-sensitive sandhi (ः → श/ष/स/हा)
      - Echoing terminal visarga (-iḥ → -ihi, -uḥ → -uhu)
      - Conjunct aids (ज्ञ → द्न्य)
      - OM → ओम
    Structural:
      - ॥ N ॥ (verse number) → .
      - ॥ → .   (long pause)
      - । → ,   (half-line pause)
      - blank lines → .
    """
    # Use the full phonetic module if available
    if _phonetic_stotra is not None:
        return _phonetic_stotra(text)

    # --- Fallback: inline rules (kept for environments without the module) ---
    import re as _re
    result = text
    # ASCII colon after Devanagari → visarga
    result = _re.sub(r'([\u0900-\u097F]):', r'\1ः', result)
    # Terminal visarga → "हा"
    result = _re.sub(r'ः(?=[\s,।॥.\n]|$)', 'हा', result)
    # Mid-word visarga → "ह"
    result = result.replace('ः', 'ह')
    # OM symbol
    result = result.replace('ॐ', 'ओम')
    # Verse numbers:  ॥ ३ ॥  or  ॥3॥ → period
    result = _re.sub(r'॥\s*[\d०-९]+\s*॥', '.', result)
    # Double danda → period
    result = result.replace('॥', '.')
    # Single danda → comma
    result = result.replace('।', ',')
    # Blank lines → period
    result = _re.sub(r'\n\s*\n+', '\n.\n', result)
    # Cleanup
    result = _re.sub(r'[.,]{2,}', '.', result)
    result = _re.sub(r'^\s*[.,]\s*', '', result)
    result = _re.sub(r'[ \t]+', ' ', result)
    result = _re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def generate_tts(text: str,
                 speed: float = 1.0,
                 pitch: float = 1.0,
                 volume: float = 1.0,
                 output_path: str = None,
                 emotion: str = None,
                 is_verse: bool = False,
                 language: str = "mr",
                 gender: str = "female") -> dict:
    """Generate Marathi TTS audio. Returns {success, audio_path} or {success:False, error}."""
    t0 = time.time()
    log.info("=== generate_tts START | text_len=%d speed=%.2f pitch=%.2f "
             "volume=%.2f emotion=%s verse=%s lang=%s gender=%s ===",
             len(text), speed, pitch, volume, emotion, is_verse, language, gender)

    # Apply gender-based pitch shift: gTTS is female by default.
    # Male voice = pitch down ~4 semitones (factor ~0.79)
    if gender == 'male':
        pitch = pitch * 0.79 if abs(pitch - 1.0) > 0.01 else 0.79
        log.info("[Gender] Male voice: adjusted pitch to %.2f", pitch)

    if not text or not text.strip():
        log.error("Empty input text")
        return {"success": False, "error": "Empty text", "stage": "validation"}

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)

    # ── Verse / Shloka mode ──────────────────────────────────────────────
    if is_verse:
        log.info("[Verse] Verse/Shloka mode enabled")
        try:
            preprocessed = _preprocess_stotra_text(_normalize_marathi(text))
            preprocessed = _apply_g2p(preprocessed)  # G2P for verse text
            log.info("[Verse] Preprocessed stotra text | orig=%d  new=%d chars",
                     len(text), len(preprocessed))
            if preprocessed.strip():
                from gtts import gTTS  # type: ignore
                use_slow = speed <= 1.05
                t_v = time.time()
                gTTS(text=preprocessed, lang=language, slow=use_slow,
                     lang_check=False).save(output_path)
                log.info("[Verse] gTTS saved in %.2fs (slow=%s)", time.time() - t_v, use_slow)

                needs_fx = (abs(speed - 1.0) > 0.05 or abs(pitch - 1.0) > 0.05
                            or abs(volume - 1.0) > 0.05)
                if needs_fx:
                    _apply_pitch_speed(output_path, speed, pitch, volume, output_path)

                elapsed = time.time() - t0
                log.info("[Verse] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
                return {"success": True, "audio_path": output_path,
                        "engine": "gtts_verse", "elapsed_sec": round(elapsed, 2)}
        except Exception as exc:
            log.error("[Verse] Failed, falling back to normal: %s", exc)

    # Stage 1: gTTS + pydub effects (primary engine on mobile)
    log.info("[Stage 1] gTTS + pydub effects")
    try:
        normalized = _normalize_marathi(text)
        normalized = apply_marathi_phonetics(normalized)  # Marathi phonetic rules
        normalized = _apply_g2p(normalized)  # G2P conjunct/anusvara/schwa rules
        fd, raw = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)
        log.info("[Stage 1] Calling gTTS | text_len=%d slow=%s", len(normalized), speed < 0.75)
        t_gtts = time.time()
        from gtts import gTTS  # type: ignore
        gTTS(text=normalized, lang=language, slow=(speed < 0.75), lang_check=False).save(raw)
        log.info("[Stage 1] gTTS saved in %.2fs", time.time() - t_gtts)

        needs_fx = abs(speed-1.0)>0.05 or abs(pitch-1.0)>0.05 or abs(volume-1.0)>0.05
        if needs_fx:
            _apply_pitch_speed(raw, speed, pitch, volume, output_path)
            try: os.unlink(raw)
            except OSError: pass
        else:
            import shutil
            shutil.move(raw, output_path)

        elapsed = time.time() - t0
        log.info("[Stage 1] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
        return {"success": True, "audio_path": output_path, "engine": "gtts_pydub",
                "elapsed_sec": round(elapsed, 2)}
    except Exception as exc:
        log.error("[Stage 1] gTTS+pydub failed: %s\n%s", exc, traceback.format_exc())

    # Stage 2: Bare gTTS fallback
    log.info("[Stage 2] Bare gTTS fallback")
    try:
        from gtts import gTTS  # type: ignore
        gTTS(text=text, lang=language, slow=False, lang_check=False).save(output_path)
        elapsed = time.time() - t0
        log.info("[Stage 2] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
        return {"success": True, "audio_path": output_path, "engine": "gtts_bare",
                "elapsed_sec": round(elapsed, 2)}
    except Exception as exc:
        log.error("[Stage 2] All TTS stages failed: %s\n%s", exc, traceback.format_exc())
        return {"success": False, "error": str(exc), "stage": "all_failed"}


def main():
    parser = argparse.ArgumentParser(description="Marathi TTS Bridge")
    parser.add_argument("--text",   required=True)
    parser.add_argument("--speed",  type=float, default=1.0)
    parser.add_argument("--pitch",  type=float, default=1.0)
    parser.add_argument("--volume", type=float, default=1.0)
    parser.add_argument("--output", default=None)
    parser.add_argument("--emotion", default=None)
    parser.add_argument("--verse",  action="store_true")
    args = parser.parse_args()
    result = generate_tts(args.text, args.speed, args.pitch, args.volume,
                          args.output, args.emotion, args.verse)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
