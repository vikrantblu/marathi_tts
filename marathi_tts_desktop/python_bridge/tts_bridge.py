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

# -- Temp file cleanup (BUG-27) --------------------------------------------
# Delete stale audio files older than 24h and enforce 100 MB size cap.
_CLEANUP_MAX_AGE_SEC = 24 * 3600   # 24 hours
_CLEANUP_MAX_SIZE_MB = 100         # total cap in MB

def _cleanup_output_dir():
    """Remove stale temp audio files from output/ to prevent storage bloat."""
    try:
        now = time.time()
        files = []
        total_size = 0
        for name in os.listdir(_OUTPUT_DIR):
            fpath = os.path.join(_OUTPUT_DIR, name)
            # Skip symlinks to prevent symlink-following attacks
            if os.path.islink(fpath) or not os.path.isfile(fpath):
                continue
            # Verify path stays within output directory
            if not os.path.realpath(fpath).startswith(os.path.realpath(_OUTPUT_DIR)):
                continue
            stat = os.stat(fpath)
            age = now - stat.st_mtime
            files.append((fpath, stat.st_mtime, stat.st_size))
            total_size += stat.st_size

            # Delete files older than max age
            if age > _CLEANUP_MAX_AGE_SEC:
                try:
                    os.unlink(fpath)
                    total_size -= stat.st_size
                except OSError:
                    pass

        # If still over size cap, delete oldest first
        if total_size > _CLEANUP_MAX_SIZE_MB * 1024 * 1024:
            files.sort(key=lambda x: x[1])  # oldest first
            for fpath, _, fsize in files:
                if total_size <= _CLEANUP_MAX_SIZE_MB * 1024 * 1024:
                    break
                if os.path.exists(fpath):
                    try:
                        os.unlink(fpath)
                        total_size -= fsize
                    except OSError:
                        pass
    except Exception:
        pass  # cleanup is best-effort, never crash the bridge

_cleanup_output_dir()

# -- Network pre-check (BUG-21) --------------------------------------------
def _is_network_available(timeout: float = 3.0) -> bool:
    """Quick connectivity check — can we reach Google DNS? Returns True/False.
    Uses a 3-second timeout by default so the check itself is fast."""
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        s.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False

log.info("TTS Bridge initialised | bridge_dir=%s | output_dir=%s",
         _BRIDGE_DIR, _OUTPUT_DIR)

# -- Phonetic engine --------------------------------------------------------
try:
    from tts.utils.phonetic.marathi_phonetics import (
        apply_sanskrit_phonetics,
        apply_marathi_phonetics,
        apply_old_marathi_phonetics,
        apply_gtts_mr_fixes,
        preprocess_stotra_text as _phonetic_stotra,
        preprocess_old_marathi_text as _phonetic_old_marathi,
    )
    log.info("Phonetic engine (marathi_phonetics) loaded OK")
except ImportError as _e:
    log.warning("marathi_phonetics not available (%s) — using fallback", _e)
    def apply_sanskrit_phonetics(t): return t
    def apply_marathi_phonetics(t): return t
    def apply_old_marathi_phonetics(t): return t
    def apply_gtts_mr_fixes(t): return t
    _phonetic_stotra = None
    _phonetic_old_marathi = None


# ---------------------------------------------------------------------------
# User phonetic corrections (FEAT-59) — loaded from JSON written by app
# ---------------------------------------------------------------------------
_user_corrections = None

def _load_user_corrections():
    """Load user-submitted pronunciation corrections from JSON file."""
    global _user_corrections
    path = os.environ.get("USER_CORRECTIONS_PATH", "")
    if not path:
        # Desktop default: look next to the bridge dir
        path = os.path.join(_BRIDGE_DIR, "user_corrections.json")
    if not os.path.isfile(path):
        _user_corrections = {}
        return _user_corrections
    try:
        import json
        with open(path, 'r', encoding='utf-8') as f:
            _user_corrections = json.load(f)
        log.info("Loaded %d user corrections from %s", len(_user_corrections), path)
    except Exception as exc:
        log.warning("Failed to load user corrections: %s", exc)
        _user_corrections = {}
    return _user_corrections


# ---------------------------------------------------------------------------
# G2P Engine (lazy singleton)
# ---------------------------------------------------------------------------
_g2p_engine = None

def _get_g2p():
    """Lazy-load the G2P engine. Returns None if unavailable."""
    global _g2p_engine
    if _g2p_engine is not None:
        # Refresh user corrections on each call (file may have changed)
        _refresh_user_corrections()
        return _g2p_engine
    try:
        from tts.utils.phonetic.g2p_engine import MarathiG2PEngine
        _g2p_engine = MarathiG2PEngine()
        # Load and apply user corrections on first init
        corrections = _load_user_corrections()
        if corrections:
            _g2p_engine.add_lexicon_entries(corrections)
        log.info("G2P engine loaded OK")
        return _g2p_engine
    except Exception as exc:
        log.warning("G2P engine not available: %s", exc)
        return None


def _refresh_user_corrections():
    """Re-read user corrections file and update G2P lexicon if changed."""
    global _user_corrections
    old_corrections = _user_corrections
    new_corrections = _load_user_corrections()
    if new_corrections and new_corrections != old_corrections and _g2p_engine:
        _g2p_engine.add_lexicon_entries(new_corrections)


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
# Edge-TTS (Microsoft Edge neural voices) — real male/female voices
# Same voice map as the desktop bridge.
# ---------------------------------------------------------------------------
_EDGE_VOICE_MAP = {
    ("mr", "female"): "mr-IN-AarohiNeural",
    ("mr", "male"):   "mr-IN-ManoharNeural",
    ("hi", "female"): "hi-IN-SwaraNeural",
    ("hi", "male"):   "hi-IN-MadhurNeural",
    # Sanskrit → Hindi voices (best Devanagari phonology available)
    ("sa", "female"): "hi-IN-SwaraNeural",
    ("sa", "male"):   "hi-IN-MadhurNeural",
    # Old Marathi → Marathi voices (phonetic preprocessing handles the rest)
    ("mr-old", "female"): "mr-IN-AarohiNeural",
    ("mr-old", "male"):   "mr-IN-ManoharNeural",
}

# ---------------------------------------------------------------------------
# Accent Profiles (FEAT-57)
# Each profile adjusts pitch, rate, and defines phonetic hints that are applied
# as SSML phoneme-level tweaks via edge-tts prosody.
# ---------------------------------------------------------------------------
ACCENT_PROFILES = {
    "standard": {
        "label": "Standard (प्रमाण)",
        "pitch_offset": 0.0,
        "rate_offset": 0.0,
        "description": "Standard Marathi accent (Pune/media)"
    },
    "mumbai": {
        "label": "Mumbai (मुंबई)",
        "pitch_offset": 0.03,
        "rate_offset": 0.08,
        "description": "Mumbai Marathi — faster pace, slightly higher pitch"
    },
    "northern": {
        "label": "Northern (उत्तर महाराष्ट्र)",
        "pitch_offset": -0.02,
        "rate_offset": -0.05,
        "description": "Khandesh/Vidarbha — slower, deeper tone"
    },
    "konkanastha": {
        "label": "Konkanastha (कोकणस्थ)",
        "pitch_offset": 0.05,
        "rate_offset": -0.03,
        "description": "Konkan region — higher pitch, measured pace"
    },
    "deccani": {
        "label": "Deccani (दख्खनी)",
        "pitch_offset": -0.04,
        "rate_offset": 0.0,
        "description": "Marathwada/Deccani — lower pitch, Urdu influence"
    },
}

def get_accent_profiles():
    """Return available accent profiles for UI population."""
    return {
        "success": True,
        "profiles": {
            k: {"label": v["label"], "description": v["description"]}
            for k, v in ACCENT_PROFILES.items()
        }
    }

def _apply_accent(speed: float, pitch: float, accent: str):
    """Adjust speed and pitch based on accent profile. Returns (speed, pitch)."""
    profile = ACCENT_PROFILES.get(accent)
    if not profile:
        return speed, pitch
    return (
        speed + profile["rate_offset"],
        pitch + profile["pitch_offset"]
    )

def _edge_tts_available() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False

def _generate_edge_tts(text: str, language: str, gender: str,
                       speed: float, pitch: float, volume: float,
                       output_path: str, is_verse: bool = False) -> dict:
    """Generate audio via edge-tts (Microsoft Edge neural voices).
    Returns {success, audio_path, engine} or empty dict on failure.
    """
    import asyncio
    try:
        import edge_tts
    except ImportError:
        log.warning("[edge-tts] package not installed")
        return {}

    voice = _EDGE_VOICE_MAP.get((language, gender)) \
        or _EDGE_VOICE_MAP.get((language, "female"))
    if voice is None:
        log.warning("[edge-tts] No voice for lang=%s gender=%s", language, gender)
        return {}

    rate_str   = f"{int((speed  - 1.0) * 100):+d}%"
    vol_str    = f"{int((volume - 1.0) * 100):+d}%"
    pitch_str  = f"{int((pitch  - 1.0) * 100):+d}Hz"

    if language == "mr-old":
        if _phonetic_old_marathi is not None:
            processed = _phonetic_old_marathi(text)
        else:
            processed = apply_old_marathi_phonetics(text)
        processed = _apply_g2p(processed)
        log.info("[edge-tts] [Old Marathi] Preprocessed | orig=%d  new=%d chars", len(text), len(processed))
    elif is_verse:
        processed = _preprocess_stotra_text(text)
        processed = _apply_g2p(processed)
    else:
        processed = _apply_g2p(text)

    log.info("[edge-tts] voice=%s rate=%s pitch=%s text_len=%d",
             voice, rate_str, pitch_str, len(processed))

    async def _run():
        comm = edge_tts.Communicate(
            text=processed, voice=voice,
            rate=rate_str, volume=vol_str, pitch=pitch_str,
        )
        await comm.save(output_path)

    t0 = time.time()
    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:
        log.error("[edge-tts] Failed: %s", exc)
        return {}

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        log.warning("[edge-tts] Output missing or too small")
        try: os.unlink(output_path)
        except OSError: pass
        return {}

    elapsed = time.time() - t0
    engine_name = f"edge_tts_{language}" + ("_verse" if is_verse else "")
    log.info("[edge-tts] SUCCESS -> %s (%.2fs) voice=%s", output_path, elapsed, voice)
    return {"success": True, "audio_path": output_path, "engine": engine_name,
            "elapsed_sec": round(elapsed, 2)}


# ---------------------------------------------------------------------------
# Prosody-segmented edge-tts (FEAT-8)
# ---------------------------------------------------------------------------

def _generate_edge_prosody(text, language, gender, speed, pitch, volume,
                           output_path, emotion_intensity=1.0):
    """Generate edge-tts audio with prosody-segmented pauses.

    Uses ProsodyEngine to determine natural pause points, generates
    per-segment audio via edge-tts neural voice, and stitches with
    calibrated pydub silence.  Only used for prose (not verse).

    Edge-tts natively handles speed/pitch/volume via SSML, so no pydub
    post-processing is needed for those parameters.

    emotion_intensity (0.0–1.0) scales the ProsodyEngine emotion modifiers.

    Returns result dict on success, None to fall through.
    """
    try:
        from tts.utils.audio.prosody_engine import MarathiProsodyEngine
        from pydub import AudioSegment as PydubSegment
        import edge_tts
        import asyncio
    except ImportError as e:
        log.info("[edge-prosody] Not available: %s", e)
        return None

    seg_files = []          # track temp files for cleanup in finally
    try:
        prosody = MarathiProsodyEngine(speaking_rate=1.0)
        segments = prosody.segment_text(text)

        if not segments or len(segments) < 2:
            log.info("[edge-prosody] < 2 segments (%d), using single-call",
                     len(segments) if segments else 0)
            return None

        # Stricter cap — each segment = 1 WebSocket connection
        if len(segments) > 15:
            log.info("[edge-prosody] %d segments exceeds cap (15)", len(segments))
            return None

        voice = _EDGE_VOICE_MAP.get((language, gender)) \
            or _EDGE_VOICE_MAP.get((language, "female"))
        if not voice:
            return None

        # Edge-tts native SSML parameters (applied per segment)
        rate_str  = f"{int((speed  - 1.0) * 100):+d}%"
        vol_str   = f"{int((volume - 1.0) * 100):+d}%"
        base_pitch_hz = int((pitch - 1.0) * 100)

        log.info("[edge-prosody] %d segments, voice=%s rate=%s",
                 len(segments), voice, rate_str)

        combined = PydubSegment.empty()
        generated = 0

        for i, seg in enumerate(segments):
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            # Preprocess segment (same as single-call edge-tts prose path)
            if language == "mr-old":
                processed = apply_old_marathi_phonetics(seg_text)
                processed = _apply_g2p(processed)
            else:
                processed = _apply_g2p(seg_text)

            if not processed.strip():
                continue

            # Per-segment pitch adjustment from ProsodyEngine emphasis,
            # scaled by emotion_intensity
            scaled_pitch_shift = seg.pitch_shift * emotion_intensity
            seg_pitch_hz = base_pitch_hz + int(scaled_pitch_shift * 100)
            seg_pitch_str = f"{seg_pitch_hz:+d}Hz"

            # Chandrabindu (ँ U+0901) → reduce volume ~3 dB for soft nasal
            if '\u0901' in processed:
                raw_vol = int((volume - 1.0) * 100)
                seg_vol_str = f"{max(raw_vol - 25, -50):+d}%"
            else:
                seg_vol_str = vol_str

            fd, seg_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
            os.close(fd)
            seg_files.append(seg_path)

            async def _run_seg(p=processed, sp=seg_path, ps=seg_pitch_str,
                               sv=seg_vol_str):
                comm = edge_tts.Communicate(
                    text=p, voice=voice,
                    rate=rate_str, volume=sv, pitch=ps)
                await comm.save(sp)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run_seg())
            finally:
                loop.close()

            if not os.path.exists(seg_path) or os.path.getsize(seg_path) < 500:
                continue

            seg_audio = PydubSegment.from_mp3(seg_path)
            combined += seg_audio
            generated += 1

            # Insert calibrated silence pause between segments
            if seg.pause_after_ms > 0 and i < len(segments) - 1:
                combined += PydubSegment.silent(duration=seg.pause_after_ms)

            log.debug("[edge-prosody] Seg %d/%d OK (%d chars, pause=%dms)",
                      i + 1, len(segments), len(processed), seg.pause_after_ms)

        if generated < 2 or len(combined) < 500:
            log.info("[edge-prosody] Too few segments (%d), falling through",
                     generated)
            return None

        combined.export(output_path, format="mp3")

        log.info("[edge-prosody] Combined %d segments -> %s (%.1fs audio)",
                 generated, output_path, len(combined) / 1000)

        return {
            "success": True,
            "audio_path": output_path,
            "engine": "edge_tts_prosody",
            "segments": generated,
        }

    except Exception as exc:
        log.warning("[edge-prosody] Failed: %s", exc)
        log.debug(traceback.format_exc())
        return None

    finally:
        for f in seg_files:
            try:
                os.unlink(f)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Verse-specific prosody-segmented edge-tts
# ---------------------------------------------------------------------------

def _generate_edge_verse_prosody(text, language, gender, speed, pitch, volume,
                                  output_path, emotion_intensity=1.0):
    """Generate edge-tts audio with verse-specific prosody segmentation.

    Uses ProsodyEngine for metre-aware verse segmentation (pauses at ।/॥,
    pitch contour, tts_rate per metre), generates per-segment audio via
    edge-tts neural voice, and stitches with calibrated verse pauses for
    natural shloka recitation.

    emotion_intensity (0.0–1.0) scales the ProsodyEngine emotion modifiers.

    Returns result dict on success, None to fall through.
    """
    try:
        from tts.utils.audio.prosody_engine import MarathiProsodyEngine
        from pydub import AudioSegment as PydubSegment
        import edge_tts
        import asyncio
    except ImportError as e:
        log.info("[edge-verse-prosody] Not available: %s", e)
        return None

    seg_files = []
    try:
        prosody = MarathiProsodyEngine(speaking_rate=1.0)
        segments = prosody.segment_text(text)

        if not segments or len(segments) < 2:
            log.info("[edge-verse-prosody] < 2 segments (%d), using single-call",
                     len(segments) if segments else 0)
            return None

        # Verse stotras can be longer than prose; cap at 40 segments
        if len(segments) > 40:
            log.info("[edge-verse-prosody] %d segments exceeds cap (40)",
                     len(segments))
            return None

        voice = _EDGE_VOICE_MAP.get((language, gender)) \
            or _EDGE_VOICE_MAP.get((language, "female"))
        if not voice:
            return None

        base_pitch_hz = int((pitch - 1.0) * 100)
        vol_str = f"{int((volume - 1.0) * 100):+d}%"

        log.info("[edge-verse-prosody] %d segments, voice=%s lang=%s",
                 len(segments), voice, language)

        combined = PydubSegment.empty()
        generated = 0

        for i, seg in enumerate(segments):
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            # Verse-specific preprocessing per language
            if language == "sa":
                processed = _preprocess_stotra_text(seg_text)
            elif language == "mr-old":
                if _phonetic_old_marathi is not None:
                    processed = _preprocess_stotra_text(
                        _phonetic_old_marathi(seg_text))
                else:
                    processed = _preprocess_stotra_text(
                        apply_old_marathi_phonetics(seg_text))
            else:
                processed = _preprocess_stotra_text(seg_text)

            processed = _apply_g2p(processed)
            if not processed.strip():
                continue

            # Per-segment rate from ProsodyEngine (verse metre rate × user speed),
            # scaled by emotion_intensity
            effective_tts_rate = 1.0 + (seg.tts_rate - 1.0) * emotion_intensity \
                if seg.tts_rate else 1.0
            seg_rate = speed * effective_tts_rate
            rate_str = f"{int((seg_rate - 1.0) * 100):+d}%"

            # Per-segment pitch: user pitch + ProsodyEngine contour,
            # scaled by emotion_intensity
            scaled_pitch_shift = seg.pitch_shift * emotion_intensity
            seg_pitch_hz = base_pitch_hz + int(scaled_pitch_shift * 100)
            seg_pitch_str = f"{seg_pitch_hz:+d}Hz"

            # Chandrabindu nasalization (FEAT-15)
            if '\u0901' in processed:
                raw_vol = int((volume - 1.0) * 100)
                seg_vol_str = f"{max(raw_vol - 25, -50):+d}%"
            else:
                seg_vol_str = vol_str

            fd, seg_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
            os.close(fd)
            seg_files.append(seg_path)

            async def _run_seg(p=processed, sp=seg_path, ps=seg_pitch_str,
                               sv=seg_vol_str, rs=rate_str):
                comm = edge_tts.Communicate(
                    text=p, voice=voice,
                    rate=rs, volume=sv, pitch=ps)
                await comm.save(sp)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run_seg())
            finally:
                loop.close()

            if not os.path.exists(seg_path) or os.path.getsize(seg_path) < 500:
                continue

            seg_audio = PydubSegment.from_mp3(seg_path)
            combined += seg_audio
            generated += 1

            # Insert verse-calibrated pause from ProsodyEngine
            if seg.pause_after_ms > 0 and i < len(segments) - 1:
                combined += PydubSegment.silent(duration=seg.pause_after_ms)

            log.debug("[edge-verse-prosody] Seg %d/%d OK (%d chars, "
                      "pause=%dms, rate=%s, pitch=%s)",
                      i + 1, len(segments), len(processed),
                      seg.pause_after_ms, rate_str, seg_pitch_str)

        if generated < 2 or len(combined) < 500:
            log.info("[edge-verse-prosody] Too few segments (%d), "
                     "falling through", generated)
            return None

        combined.export(output_path, format="mp3")

        log.info("[edge-verse-prosody] Combined %d segments -> %s "
                 "(%.1fs audio)", generated, output_path,
                 len(combined) / 1000)

        return {
            "success": True,
            "audio_path": output_path,
            "engine": "edge_tts_verse_prosody",
            "segments": generated,
        }

    except Exception as exc:
        log.warning("[edge-verse-prosody] Failed: %s", exc)
        log.debug(traceback.format_exc())
        return None

    finally:
        for f in seg_files:
            try:
                os.unlink(f)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_pitch_speed(src: str, speed: float, pitch: float, volume: float, dst: str) -> str:
    """Apply speed/pitch/volume adjustments via pydub. Returns dst path.

    **Limitations (BUG-26):**
    - pydub pitch shift uses frame-rate manipulation, NOT proper pitch shifting.
      This causes slight duration change when pitch != 1.0.  Clamped to safe
      range to avoid audio artifacts.
    - Safe ranges:  speed ∈ [0.75, 1.25],  pitch ∈ [0.79, 1.26] (~-4 to +4 st)
    - Will be superseded by edge-tts SSML <prosody rate/pitch> (FEAT-8) which
      does native neural-quality pitch/speed without artifacts.
    """
    try:
        from pydub import AudioSegment  # type: ignore
        import math
        # Clamp to safe range (BUG-26)
        speed = max(0.75, min(1.25, speed))
        pitch = max(0.79, min(1.26, pitch))
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
    import unicodedata
    # BUG-29 fix: canonical NFC normalization at pipeline entry point
    text = unicodedata.normalize('NFC', text)
    try:
        from tts.utils.text.text_normalizer import MarathiTextNormalizer  # type: ignore
        # BUG-24 fix: lazy singleton — avoid re-init of IndicNormalizerFactory per call
        if not hasattr(_normalize_marathi, '_instance'):
            _normalize_marathi._instance = MarathiTextNormalizer()
        result = _normalize_marathi._instance.normalize_text(text)
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
# Prose preprocessing — abbreviation expansion + English transliteration
# ---------------------------------------------------------------------------
import re as _re_prose

# Ordered longest-match first so  प. पू.  beats  पू.
_MARATHI_ABBREV = [
    (_re_prose.compile(r'\bप\s*\.\s*पू\s*\.'), 'परमपूज्य'),
    (_re_prose.compile(r'\bपू\s*\.'), 'पूज्य'),
    (_re_prose.compile(r'\bश्रीमती\s*\.'), 'श्रीमती'),
    (_re_prose.compile(r'\bश्री\s*\.'), 'श्री'),
    (_re_prose.compile(r'\bसौ\s*\.'), 'सौभाग्यवती'),
    (_re_prose.compile(r'\bकु\s*\.'), 'कुमारी'),
    (_re_prose.compile(r'\bडॉ\s*\.'), 'डॉक्टर'),
    (_re_prose.compile(r'\bप्रा\s*\.'), 'प्राध्यापक'),
    (_re_prose.compile(r'\bस्व\s*\.'), 'स्वर्गीय'),
    (_re_prose.compile(r'\bकि\s*\.\s*मी\s*\.'), 'किलोमीटर'),
    (_re_prose.compile(r'\bइ\s*\.\s*स\s*\.'), 'इसवी सन'),
    (_re_prose.compile(r'\bइ\s*\.\s*स\s*\.\s*पू\s*\.'), 'इसवी सनपूर्व'),
    (_re_prose.compile(r'\bरु\s*\.'), 'रुपये'),
    (_re_prose.compile(r'\bनं\s*\.'), 'नंबर'),
    (_re_prose.compile(r'\bक्र\s*\.'), 'क्रमांक'),
    (_re_prose.compile(r'\bपृ\s*\.'), 'पृष्ठ'),
    (_re_prose.compile(r'\bसं\s*\.'), 'संख्या'),
    (_re_prose.compile(r'\bजि\s*\.'), 'जिल्हा'),
    (_re_prose.compile(r'\bता\s*\.'), 'तालुका'),
    (_re_prose.compile(r'\bमु\s*\.\s*पो\s*\.'), 'मुक्काम पोस्ट'),
]

_ENGLISH_TO_DEVNAGARI = {
    "heart": "हार्ट", "attack": "अटॅक", "blood": "ब्लड", "pressure": "प्रेशर",
    "sugar": "शुगर", "diabetes": "डायबिटीस", "hospital": "हॉस्पिटल",
    "doctor": "डॉक्टर", "medicine": "मेडिसिन", "tablet": "टॅब्लेट",
    "capsule": "कॅप्सूल", "injection": "इंजेक्शन", "dose": "डोस",
    "fever": "फीव्हर", "pain": "पेन", "test": "टेस्ट", "report": "रिपोर्ट",
    "delivery": "डिलिव्हरी", "normal": "नॉर्मल", "caesarean": "सिझेरियन",
    "operation": "ऑपरेशन", "emergency": "इमर्जन्सी", "ambulance": "अँब्युलन्स",
    "oxygen": "ऑक्सिजन", "icu": "आयसीयू", "ward": "वॉर्ड",
    "convulsions": "कन्व्हल्शन्स", "infection": "इन्फेक्शन", "virus": "व्हायरस",
    "vaccine": "व्हॅक्सिन", "protein": "प्रोटीन", "calcium": "कॅल्शियम",
    "vitamin": "व्हिटॅमिन", "hemoglobin": "हिमोग्लोबिन", "anemia": "अॅनिमिया",
    "ultrasound": "अल्ट्रासाउंड", "xray": "एक्सरे", "scan": "स्कॅन",
    "school": "स्कूल", "college": "कॉलेज", "class": "क्लास", "exam": "एक्झाम",
    "result": "रिझल्ट", "pass": "पास", "fail": "फेल", "marks": "मार्क्स",
    "percent": "पर्सेंट", "fee": "फी", "form": "फॉर्म",
    "mobile": "मोबाईल", "phone": "फोन", "internet": "इंटरनेट",
    "computer": "कॉम्प्युटर", "software": "सॉफ्टवेअर", "app": "अॅप",
    "online": "ऑनलाईन", "offline": "ऑफलाईन", "download": "डाऊनलोड",
    "upload": "अपलोड", "account": "अकाऊंट", "password": "पासवर्ड",
    "video": "व्हिडिओ", "photo": "फोटो", "camera": "कॅमेरा",
    "bus": "बस", "train": "ट्रेन", "car": "कार", "bike": "बाईक",
    "ticket": "तिकीट", "station": "स्टेशन", "platform": "प्लॅटफॉर्म",
    "office": "ऑफिस", "file": "फाईल", "copy": "कॉपी", "post": "पोस्ट",
}

_DEVANAGARI_CONSONANTS = (
    'ब','भ','च','छ','ड','ढ','फ','ग','घ','ह','ज','झ','क','ख','ल','ळ','म','न',
    'ण','प','र','स','श','ष','त','थ','द','ध','व','य','झ','ट','ठ',
)

def _transliterate_english_char_level(word: str) -> str:
    """Best-effort ASCII → Devanagari char-level mapping."""
    _C2D = {
        'a': 'अ', 'b': 'ब', 'c': 'क', 'd': 'ड', 'e': 'ए', 'f': 'फ',
        'g': 'ग', 'h': 'ह', 'i': 'इ', 'j': 'ज', 'k': 'क', 'l': 'ल',
        'm': 'म', 'n': 'न', 'o': 'ओ', 'p': 'प', 'q': 'क', 'r': 'र',
        's': 'स', 't': 'ट', 'u': 'उ', 'v': 'व', 'w': 'व', 'x': 'क्स',
        'y': 'य', 'z': 'झ',
    }
    out = []
    for ch in word.lower():
        out.append(_C2D.get(ch, ch))
    return ''.join(out)


def _transliterate_english_words(text: str) -> str:
    """Replace ASCII runs of 3+ chars with Devanagari equivalents."""
    def _replace(m):
        word = m.group(0)
        key = word.lower()
        if key in _ENGLISH_TO_DEVNAGARI:
            return _ENGLISH_TO_DEVNAGARI[key]
        if len(key) >= 3:
            return _transliterate_english_char_level(word)
        return word
    return _re_prose.sub(r'[A-Za-z]{3,}', _replace, text)


def _preprocess_prose_text(text: str) -> str:
    """Expand Marathi abbreviations and transliterate embedded English words."""
    r = text
    # 1. Expand known Marathi abbreviations
    for pat, replacement in _MARATHI_ABBREV:
        r = pat.sub(replacement, r)
    # 2. Remove stray dots after short 1-2-char Devanagari abbreviations
    #    (only when followed by whitespace + more Devanagari/digits, to avoid
    #    eating sentence-ending dots)
    r = _re_prose.sub(
        r'(?<!\S)([\u0900-\u097F]{1,2})\.'
        r'(?=\s+[\u0900-\u097F\u0966-\u096F])',
        r'\1', r
    )
    # 3. Transliterate embedded English words
    r = _transliterate_english_words(r)
    return r

def _apply_grammar(text: str) -> str:
    """Apply MarathiGrammarEngine to clean/fix prose text.

    Handles: OCR cleanup, spelling corrections, sandhi splits, vibhakti
    agreement, word order, punctuation restoration, repetition removal.
    Falls through gracefully to original text on any failure.
    """
    try:
        from tts.utils.text.marathi_grammar import MarathiGrammarEngine  # type: ignore
        if not hasattr(_apply_grammar, '_instance'):
            _apply_grammar._instance = MarathiGrammarEngine()
        result = _apply_grammar._instance.process(text)
        if result and result.strip():
            log.debug("[Grammar] Processed | %d -> %d chars", len(text), len(result))
            return result
        return text
    except Exception as exc:
        log.info("[Grammar] Not available or failed: %s", exc)
        return text

# ---------------------------------------------------------------------------
# Prosody-segmented generation (FEAT-1)
# ---------------------------------------------------------------------------

def _generate_prosody_audio(text, speed, pitch, volume, output_path,
                            language, gtts_language):
    """Generate prose audio with natural prosody-segmented pauses.

    Uses MarathiProsodyEngine to split text at clause/sentence boundaries,
    generates audio per segment via gTTS, and stitches them with calibrated
    silence gaps using pydub.

    Returns result dict on success, None to fall through to normal generation.
    Only used for prose (not verse).  The entire function is wrapped so that
    ANY failure falls through gracefully to the existing single-call path.
    """
    try:
        from tts.utils.audio.prosody_engine import MarathiProsodyEngine
        from pydub import AudioSegment as PydubSegment
        from gtts import gTTS
    except ImportError as e:
        log.info("[Prosody] Not available: %s", e)
        return None

    seg_files = []          # track temp files for cleanup in finally
    try:
        # Segment at natural pause points.  speaking_rate=1.0 so that pause
        # durations are calibrated for normal speed; user speed/pitch are
        # applied to the final combined audio via _apply_pitch_speed().
        prosody = MarathiProsodyEngine(speaking_rate=1.0)
        segments = prosody.segment_text(text)

        if not segments or len(segments) < 2:
            log.info("[Prosody] < 2 segments (%d), using normal flow",
                     len(segments) if segments else 0)
            return None

        # Cap at 25 segments to keep API call count reasonable
        if len(segments) > 25:
            log.info("[Prosody] %d segments exceeds cap (25), using normal flow",
                     len(segments))
            return None

        log.info("[Prosody] %d segments detected, generating per-segment audio",
                 len(segments))

        combined = PydubSegment.empty()
        generated = 0

        for i, seg in enumerate(segments):
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            # Full preprocessing pipeline for each segment
            processed = seg_text
            if language == "sa":
                processed = apply_sanskrit_phonetics(processed)
            elif language == "mr-old":
                processed = apply_old_marathi_phonetics(
                    _normalize_marathi(processed))
            else:
                processed = _normalize_marathi(processed)
                processed = apply_marathi_phonetics(processed)
            processed = _apply_g2p(processed)
            if gtts_language == 'mr':
                processed = apply_gtts_mr_fixes(processed)

            if not processed.strip():
                continue

            # Generate audio for this segment
            fd, seg_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
            os.close(fd)
            seg_files.append(seg_path)

            use_slow = seg.is_verse or seg.tts_rate < 0.95
            gTTS(text=processed, lang=gtts_language, slow=use_slow,
                 lang_check=False).save(seg_path)

            seg_audio = PydubSegment.from_mp3(seg_path)
            combined += seg_audio
            generated += 1

            # Insert calibrated silence pause between segments
            if seg.pause_after_ms > 0 and i < len(segments) - 1:
                combined += PydubSegment.silent(duration=seg.pause_after_ms)

            log.debug("[Prosody] Seg %d/%d OK (%d chars, pause=%dms)",
                      i + 1, len(segments), len(processed), seg.pause_after_ms)

        if generated < 2 or len(combined) < 500:
            log.info("[Prosody] Too few segments generated (%d), falling through",
                     generated)
            return None

        # Export combined audio
        combined.export(output_path, format="mp3")

        # Apply user-requested pitch/speed/volume effects to final audio
        needs_fx = (abs(speed - 1.0) > 0.05 or abs(pitch - 1.0) > 0.05
                    or abs(volume - 1.0) > 0.05)
        if needs_fx:
            _apply_pitch_speed(output_path, speed, pitch, volume, output_path)

        log.info("[Prosody] Combined %d segments -> %s (%.1fs audio)",
                 generated, output_path, len(combined) / 1000)

        return {
            "success": True,
            "audio_path": output_path,
            "engine": "gtts_prosody",
            "segments": generated,
        }

    except Exception as exc:
        log.warning("[Prosody] Generation failed: %s", exc)
        log.debug(traceback.format_exc())
        return None

    finally:
        for f in seg_files:
            try:
                os.unlink(f)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def generate_tts(text: str,
                 speed: float = 1.0,
                 pitch: float = 1.0,
                 volume: float = 1.0,
                 output_path: str = None,
                 emotion: str = None,
                 emotion_intensity: float = 1.0,
                 is_verse: bool = False,
                 language: str = "mr",
                 gender: str = "female",
                 accent: str = "standard") -> dict:
    """Generate Marathi TTS audio. Returns {success, audio_path} or {success:False, error}."""
    t0 = time.time()
    log.info("=== generate_tts START | text_len=%d speed=%.2f pitch=%.2f "
             "volume=%.2f emotion=%s verse=%s lang=%s gender=%s accent=%s ===",
             len(text), speed, pitch, volume, emotion, is_verse, language, gender, accent)

    # Apply accent profile modifiers to speed and pitch
    speed, pitch = _apply_accent(speed, pitch, accent)

    # Map unsupported gTTS languages to closest supported one.
    # Sanskrit → Hindi (phonologically much closer than Marathi; same Devanagari TTS voice)
    _gtts_lang_map = {"sa": "hi", "mr-old": "mr", "ne": "hi"}
    gtts_language = _gtts_lang_map.get(language, language)

    # ── Custom Voice Engine (FEAT-50) ────────────────────────────────────
    # Highest priority for verse content: try pre-recorded segment library
    # and custom ONNX model BEFORE any network-dependent engine.
    # Works offline — no internet required.
    try:
        from custom_voice_engine import generate_custom_voice
        custom_result = generate_custom_voice(
            text, speed=speed, pitch=pitch, volume=volume,
            output_path=output_path, is_verse=is_verse, language=language)
        if custom_result and custom_result.get("success"):
            custom_result["elapsed_sec"] = round(time.time() - t0, 2)
            log.info("[Custom] SUCCESS engine=%s (%.2fs)",
                     custom_result.get("engine", "custom"),
                     custom_result["elapsed_sec"])
            return custom_result
    except ImportError:
        log.debug("[Custom] custom_voice_engine not available")
    except Exception as exc:
        log.warning("[Custom] Custom voice failed: %s", exc)

    # ── Network pre-check (BUG-21) ───────────────────────────────────────
    # Both edge-tts and gTTS require internet.  Fail fast with a clear
    # message instead of waiting 30 s for a socket timeout.
    if not _is_network_available():
        log.error("[Network] No internet connectivity — cannot reach TTS API")
        return {"success": False,
                "error": "No internet connection. Please check your network and try again.",
                "error_code": "ERR_NO_NETWORK",
                "stage": "network_check"}

    # ── Stage 0: edge-tts — real male/female neural voices (requires internet) ──
    # Tried first because it provides a genuine ManoharNeural male voice,
    # unlike gTTS which is always female and only pitch-shifted for male.
    if _edge_tts_available():
        _edge_output = output_path if output_path else \
            tempfile.mktemp(suffix=".mp3", dir=_OUTPUT_DIR)
        # Try prosody-segmented edge-tts first
        if is_verse:
            # Verse-specific prosody with metre-aware pauses & pitch contour
            prosody_result = _generate_edge_verse_prosody(
                text, language, gender, speed, pitch, volume, _edge_output,
                emotion_intensity=emotion_intensity)
            if prosody_result and prosody_result.get("success"):
                prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
                log.info("[Stage 0] edge-tts verse prosody SUCCESS "
                         "(%d segments, %.2fs)",
                         prosody_result.get("segments", 0),
                         prosody_result["elapsed_sec"])
                return prosody_result
        else:
            # Prose prosody (FEAT-8)
            prosody_result = _generate_edge_prosody(
                text, language, gender, speed, pitch, volume, _edge_output,
                emotion_intensity=emotion_intensity)
            if prosody_result and prosody_result.get("success"):
                prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
                log.info("[Stage 0] edge-tts prosody SUCCESS (%d segments, %.2fs)",
                         prosody_result.get("segments", 0),
                         prosody_result["elapsed_sec"])
                return prosody_result
        # Single-call edge-tts (fallback)
        result = _generate_edge_tts(text, language, gender, speed, pitch, volume,
                                    _edge_output, is_verse)
        if result.get("success"):
            log.info("[Stage 0] edge-tts SUCCESS")
            return result
        log.warning("[Stage 0] edge-tts failed — falling back to gTTS")

    # Apply gender-based pitch shift for gTTS fallback only.
    # gTTS is always female; lower pitch ~4 semitones to approximate male.
    if gender == 'male':
        pitch = pitch * 0.79 if abs(pitch - 1.0) > 0.01 else 0.79
        log.info("[Gender/gTTS fallback] Male pitch adjusted to %.2f", pitch)

    if not text or not text.strip():
        log.error("Empty input text")
        return {"success": False, "error": "Empty text",
                "error_code": "ERR_EMPTY_TEXT", "stage": "validation"}

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)

    # ── Prose preprocessing (abbreviation expansion + English transliteration) ──
    if not is_verse:
        preprocessed_text = _preprocess_prose_text(text)
        if preprocessed_text != text:
            log.info("[Prose] Preprocessed | orig=%d new=%d chars",
                     len(text), len(preprocessed_text))
        text = preprocessed_text

    # ── Grammar engine (FEAT-3) — spelling, sandhi, vibhakti, punctuation ──
    # Applied to Marathi prose only (not Sanskrit, not verse).
    if not is_verse and language not in ("sa", "en"):
        grammar_text = _apply_grammar(text)
        if grammar_text != text:
            log.info("[Grammar] Applied | orig=%d new=%d chars",
                     len(text), len(grammar_text))
        text = grammar_text

    # ── Verse / Shloka mode ──────────────────────────────────────────────
    if is_verse:
        log.info("[Verse] Verse/Shloka mode enabled, lang=%s", language)
        try:
            # Sanskrit: skip Marathi normalizer (corrupts Sanskrit sandhi/visarga).
            # _preprocess_stotra_text already applies apply_sanskrit_phonetics internally.
            # Marathi / Old-Marathi / others: normalise first, then stotra cleanup.
            if language == "sa":
                preprocessed = _preprocess_stotra_text(text)
            elif language == "mr-old":
                preprocessed = _preprocess_stotra_text(
                    apply_old_marathi_phonetics(_normalize_marathi(text))
                )
            else:
                preprocessed = _preprocess_stotra_text(_normalize_marathi(text))

            preprocessed = _apply_g2p(preprocessed)
            # Apply gTTS-specific fixes (ZWNJ for y-glide, terminal halant)
            # AFTER G2P because G2P strips ZWNJ.
            if gtts_language == 'mr':
                preprocessed = apply_gtts_mr_fixes(preprocessed)
            log.info("[Verse] Preprocessed stotra text | orig=%d  new=%d chars",
                     len(text), len(preprocessed))
            if preprocessed.strip():
                from gtts import gTTS  # type: ignore
                use_slow = speed <= 1.05
                t_v = time.time()
                gTTS(text=preprocessed, lang=gtts_language, slow=use_slow,
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

    # ── Prosody-segmented generation (FEAT-1) ────────────────────────────
    # For prose text, use ProsodyEngine to split at natural clause/sentence
    # boundaries, generate audio per segment, and stitch with calibrated
    # silence pauses.  Falls through to single-call if unavailable.
    if not is_verse:
        prosody_result = _generate_prosody_audio(
            text, speed, pitch, volume, output_path, language, gtts_language)
        if prosody_result and prosody_result.get("success"):
            prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
            log.info("[Prosody] SUCCESS -> %s (%d segments, %.2fs)",
                     output_path, prosody_result.get("segments", 0),
                     prosody_result["elapsed_sec"])
            return prosody_result

    # Stage 1: gTTS + pydub effects (primary engine on mobile)
    log.info("[Stage 1] gTTS + pydub effects, lang=%s", language)
    try:
        normalized = _normalize_marathi(text) if language not in ("sa",) else text
        if language == "sa":
            normalized = apply_sanskrit_phonetics(normalized)
        elif language == "mr-old":
            normalized = apply_old_marathi_phonetics(normalized)
        else:
            normalized = apply_marathi_phonetics(normalized)  # Modern Marathi rules
        normalized = _apply_g2p(normalized)  # G2P conjunct/anusvara/schwa rules
        # Apply gTTS-specific fixes (ZWNJ for y-glide, terminal halant)
        # AFTER G2P because G2P strips ZWNJ.
        if gtts_language == 'mr':
            normalized = apply_gtts_mr_fixes(normalized)
        fd, raw = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)
        log.info("[Stage 1] Calling gTTS | text_len=%d slow=%s", len(normalized), speed < 0.75)
        t_gtts = time.time()
        from gtts import gTTS  # type: ignore
        gTTS(text=normalized, lang=gtts_language, slow=(speed < 0.75), lang_check=False).save(raw)
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
        gTTS(text=text, lang=gtts_language, slow=False, lang_check=False).save(output_path)
        elapsed = time.time() - t0
        log.info("[Stage 2] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
        return {"success": True, "audio_path": output_path, "engine": "gtts_bare",
                "elapsed_sec": round(elapsed, 2)}
    except Exception as exc:
        log.error("[Stage 2] All TTS stages failed: %s\n%s", exc, traceback.format_exc())
        return {"success": False, "error": str(exc),
                "error_code": "ERR_ALL_ENGINES_FAILED", "stage": "all_failed"}


# ---------------------------------------------------------------------------
# FEAT-53: A/B Engine Comparison
# ---------------------------------------------------------------------------
def compare_engines(text: str,
                    speed: float = 1.0,
                    pitch: float = 1.0,
                    volume: float = 1.0,
                    is_verse: bool = False,
                    language: str = "mr",
                    gender: str = "female",
                    engines: list = None) -> dict:
    """Generate audio with multiple engines for A/B comparison.

    Returns:
        {
            "success": True,
            "results": [
                {"engine": "custom_segment_library", "audio_path": "...", "elapsed_sec": 1.2},
                {"engine": "edge_tts", "audio_path": "...", "elapsed_sec": 2.5},
                {"engine": "gtts_pydub", "audio_path": "...", "elapsed_sec": 3.1},
            ],
            "engine_count": 3
        }
    """
    log.info("=== compare_engines START | engines=%s ===", engines)
    all_engines = engines or ["custom", "edge_tts", "gtts"]
    results = []

    for eng_name in all_engines:
        fd, out_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)
        t0 = time.time()

        try:
            if eng_name == "custom":
                try:
                    from custom_voice_engine import generate_custom_voice
                    r = generate_custom_voice(
                        text, speed=speed, pitch=pitch, volume=volume,
                        output_path=out_path, is_verse=is_verse, language=language)
                    if r and r.get("success"):
                        r["elapsed_sec"] = round(time.time() - t0, 2)
                        results.append(r)
                        continue
                except ImportError:
                    pass

            elif eng_name == "edge_tts" and _edge_tts_available():
                r = _generate_edge_tts(
                    text, language, gender, speed, pitch, volume,
                    out_path, is_verse=is_verse)
                if r.get("success"):
                    r["elapsed_sec"] = round(time.time() - t0, 2)
                    results.append(r)
                    continue

            elif eng_name == "gtts":
                _gtts_lang_map = {"sa": "hi", "mr-old": "mr", "ne": "hi"}
                gtts_lang = _gtts_lang_map.get(language, language)
                from gtts import gTTS  # type: ignore
                gTTS(text=text, lang=gtts_lang, slow=False,
                     lang_check=False).save(out_path)
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    results.append({
                        "success": True,
                        "audio_path": out_path,
                        "engine": "gtts_bare",
                        "elapsed_sec": round(time.time() - t0, 2),
                    })
                    continue

            # Engine didn't produce output — clean up
            try:
                os.unlink(out_path)
            except OSError:
                pass

        except Exception as exc:
            log.warning("[Compare] %s failed: %s", eng_name, exc)
            try:
                os.unlink(out_path)
            except OSError:
                pass

    return {
        "success": len(results) > 0,
        "results": results,
        "engine_count": len(results),
    }


# ---------------------------------------------------------------------------
# FEAT-51: Prosody Analysis (preview before generation)
# ---------------------------------------------------------------------------
def analyze_prosody(text: str,
                    language: str = "mr",
                    is_verse: bool = False,
                    emotion: str = None,
                    emotion_intensity: float = 1.0) -> dict:
    """Analyze text and return prosody segments for preview.

    Returns:
        {
            "success": True,
            "segments": [
                {
                    "index": 0,
                    "text": "...",
                    "pause_after_ms": 600,
                    "emotion": "neutral",
                    "emphasis": 1.0,
                    "pitch_shift": 0.0,
                    "is_verse": False,
                    "metre_name": "",
                    "tts_rate": 1.0
                },
                ...
            ],
            "segment_count": N,
            "is_verse_detected": True/False,
            "metre": "Anushtubh" or ""
        }
    """
    try:
        from tts.utils.audio.prosody_engine import MarathiProsodyEngine

        detected_emotion = emotion or "neutral"
        prosody = MarathiProsodyEngine(speaking_rate=1.0, emotion=detected_emotion)
        segments = prosody.segment_text(text)

        if not segments:
            return {"success": True, "segments": [], "segment_count": 0,
                    "is_verse_detected": False, "metre": ""}

        result_segments = []
        detected_verse = False
        detected_metre = ""
        ei = max(0.0, min(1.0, emotion_intensity))
        for i, seg in enumerate(segments):
            # Scale emotion-derived pitch_shift and tts_rate by intensity
            scaled_pitch = seg.pitch_shift * ei
            scaled_rate = 1.0 + (seg.tts_rate - 1.0) * ei
            result_segments.append({
                "index": i,
                "text": seg.text,
                "pause_after_ms": seg.pause_after_ms,
                "emotion": seg.emotion,
                "emphasis": round(seg.emphasis, 2),
                "pitch_shift": round(scaled_pitch, 2),
                "is_verse": seg.is_verse,
                "metre_name": seg.metre_name,
                "tts_rate": round(scaled_rate, 2),
            })
            if seg.is_verse:
                detected_verse = True
            if seg.metre_name and not detected_metre:
                detected_metre = seg.metre_name

        return {
            "success": True,
            "segments": result_segments,
            "segment_count": len(result_segments),
            "is_verse_detected": detected_verse,
            "metre": detected_metre,
        }
    except Exception as exc:
        log.error("[analyze_prosody] %s", exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# FEAT-55: Phonetic Explainer
# ---------------------------------------------------------------------------
def explain_phonetics(word: str, language: str = "mr") -> dict:
    """Trace phonetic transformations applied to a single word.

    Returns: {
        "success": True,
        "original": "दुःख",
        "final": "दुख्ख",
        "rules": [
            {"stage": "Marathi Phonetics", "rule": "Visarga gemination",
             "before": "दुःख", "after": "दुख्ख",
             "description": "Visarga before ख becomes geminated ख्ख"}
        ]
    }
    """
    if not word or not word.strip():
        return {"success": False, "error": "Empty word"}

    word = word.strip()
    rules = []
    current = word

    try:
        # Stage 1: G2P exception lexicon check
        try:
            from tts.constants.g2p_constants import EXCEPTION_LEXICON
            if word in EXCEPTION_LEXICON:
                lex_result = EXCEPTION_LEXICON[word]
                if lex_result != word:
                    rules.append({
                        "stage": "G2P Lexicon",
                        "rule": "Exception lexicon match",
                        "before": current,
                        "after": lex_result,
                        "description": f"'{word}' has a custom pronunciation entry"
                    })
                    current = lex_result
                else:
                    rules.append({
                        "stage": "G2P Lexicon",
                        "rule": "Exception lexicon (identity)",
                        "before": current,
                        "after": current,
                        "description": f"'{word}' in lexicon — bypasses rule-based processing"
                    })
        except ImportError:
            pass

        # Stage 2: Sandhi engine (for Sanskrit or verse)
        if language == "sa":
            try:
                from tts.utils.phonetic.sandhi_engine import SandhiEngine
                sandhi = SandhiEngine()
                after_sandhi = sandhi.process(current)
                if after_sandhi != current:
                    # Detect specific sandhi rules
                    _detect_sandhi_rules(current, after_sandhi, rules)
                    current = after_sandhi
            except ImportError:
                pass

        # Stage 3: Language-specific phonetics
        try:
            if language == "sa":
                after_phon = apply_sanskrit_phonetics(current)
            elif language == "mr-old":
                after_phon = apply_old_marathi_phonetics(current)
            else:
                after_phon = apply_marathi_phonetics(current)

            if after_phon != current:
                _detect_phonetic_rules(current, after_phon, language, rules)
                current = after_phon
        except Exception:
            pass

        # Stage 4: G2P engine
        try:
            after_g2p = _apply_g2p(current)
            if after_g2p != current:
                _detect_g2p_rules(current, after_g2p, rules)
                current = after_g2p
        except Exception:
            pass

        return {
            "success": True,
            "original": word,
            "final": current,
            "rules": rules,
            "rule_count": len(rules),
        }
    except Exception as exc:
        log.error("[explain_phonetics] %s", exc)
        return {"success": False, "error": str(exc)}


def _detect_sandhi_rules(before: str, after: str, rules: list):
    """Detect which sandhi rules were applied."""
    if 'ऽ' in before and 'ऽ' not in after:
        rules.append({
            "stage": "Sandhi", "rule": "Avagraha expansion",
            "before": before, "after": after,
            "description": "ऽ (avagraha) removed — represents elided vowel"
        })
    if 'ः' in before and 'र्' in after and 'र्' not in before:
        rules.append({
            "stage": "Sandhi", "rule": "Visarga → r-sandhi",
            "before": before, "after": after,
            "description": "Visarga (ः) before voiced sound becomes र्"
        })
    if 'ं' in before:
        for src, dst in [('ंश', 'न्श'), ('ंष', 'न्ष'), ('ंस', 'न्स'), ('ंह', 'म्ह')]:
            if src in before and dst in after:
                rules.append({
                    "stage": "Sandhi", "rule": "Anusvara + sibilant assimilation",
                    "before": before, "after": after,
                    "description": f"anusvara before sibilant: {src} → {dst}"
                })
                break
    if not rules or rules[-1]["stage"] != "Sandhi":
        rules.append({
            "stage": "Sandhi", "rule": "Sandhi correction",
            "before": before, "after": after,
            "description": "Sanskrit sandhi rules applied"
        })


def _detect_phonetic_rules(before: str, after: str, language: str, rules: list):
    """Detect which phonetic rules were applied."""
    if 'ज्ञ' in before and 'द्न्य' in after:
        rules.append({
            "stage": "Phonetics", "rule": "Conjunct ज्ञ → द्न्य",
            "before": before, "after": after,
            "description": "Marathi pronunciation of ज्ञ is द्न्य (not gya)"
        })
    if 'ः' in before and 'ः' not in after:
        # Visarga was resolved
        if 'ख्ख' in after or 'स्स' in after or 'श्श' in after:
            rules.append({
                "stage": "Phonetics", "rule": "Visarga gemination",
                "before": before, "after": after,
                "description": "Visarga before consonant → geminated consonant"
            })
        elif 'र्' in after and 'र्' not in before:
            rules.append({
                "stage": "Phonetics", "rule": "Visarga → r",
                "before": before, "after": after,
                "description": "Visarga before voiced sound becomes r"
            })
        else:
            rules.append({
                "stage": "Phonetics", "rule": "Visarga resolution",
                "before": before, "after": after,
                "description": "Visarga (ः) resolved based on phonetic context"
            })
    if 'ॐ' in before and 'ओम' in after:
        rules.append({
            "stage": "Phonetics", "rule": "OM expansion",
            "before": before, "after": after,
            "description": "ॐ symbol expanded to ओम for TTS"
        })
    if 'ॠ' in before and 'री' in after:
        rules.append({
            "stage": "Phonetics", "rule": "Vocalic R → री",
            "before": before, "after": after,
            "description": "Rare vocalic ॠ converted to री"
        })
    # Generic catch-all if no specific rule detected
    if not any(r["stage"] == "Phonetics" for r in rules):
        rules.append({
            "stage": "Phonetics",
            "rule": f"{'Sanskrit' if language == 'sa' else 'Marathi'} phonetic rules",
            "before": before, "after": after,
            "description": "Language-specific pronunciation rules applied"
        })


def _detect_g2p_rules(before: str, after: str, rules: list):
    """Detect which G2P rules were applied."""
    if '\u200c' in after and '\u200c' not in before:
        rules.append({
            "stage": "G2P", "rule": "Morpheme boundary (ZWNJ)",
            "before": before, "after": after,
            "description": "Zero-width non-joiner inserted at stem/suffix boundary"
        })
    if '्' in after and after.count('्') > before.count('्'):
        rules.append({
            "stage": "G2P", "rule": "Schwa deletion",
            "before": before, "after": after,
            "description": "Inherent schwa removed at word-internal position"
        })
    if not any(r["stage"] == "G2P" for r in rules):
        rules.append({
            "stage": "G2P", "rule": "G2P processing",
            "before": before, "after": after,
            "description": "Grapheme-to-phoneme conversion applied"
        })


# ---------------------------------------------------------------------------
# FEAT-52: Per-Sentence Regeneration
# ---------------------------------------------------------------------------
def regenerate_segment(text: str,
                       speed: float = 1.0,
                       pitch: float = 1.0,
                       volume: float = 1.0,
                       language: str = "mr",
                       gender: str = "female",
                       is_verse: bool = False,
                       emotion: str = None) -> dict:
    """Regenerate a single text segment with given parameters.

    Lighter than generate_tts() — skips custom voice and uses the fastest
    available engine for a single short segment.

    Returns: {"success": True, "audio_path": "...", "engine": "..."} or error.
    """
    t0 = time.time()
    log.info("[regen] text_len=%d speed=%.2f pitch=%.2f vol=%.2f",
             len(text), speed, pitch, volume)

    _gtts_lang_map = {"sa": "hi", "mr-old": "mr", "ne": "hi"}
    gtts_language = _gtts_lang_map.get(language, language)

    if not _is_network_available():
        return {"success": False, "error": "No internet connection.",
                "error_code": "ERR_NO_NETWORK"}

    # Try edge-tts first (best quality, single segment = fast)
    if _edge_tts_available():
        out = tempfile.mktemp(suffix=".mp3", dir=_OUTPUT_DIR)
        try:
            r = _generate_edge_tts(text, language, gender, speed, pitch,
                                   volume, out, is_verse=is_verse)
            if r and r.get("success"):
                r["elapsed_sec"] = round(time.time() - t0, 2)
                return r
        except Exception as exc:
            log.warning("[regen][edge] %s", exc)

    # Fallback: gTTS
    try:
        from gtts import gTTS
        out = tempfile.mktemp(suffix=".mp3", dir=_OUTPUT_DIR)
        gTTS(text=text, lang=gtts_language, slow=is_verse,
             lang_check=False).save(out)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return {"success": True, "audio_path": out, "engine": "gtts_regen",
                    "elapsed_sec": round(time.time() - t0, 2)}
    except Exception as exc:
        log.warning("[regen][gtts] %s", exc)

    return {"success": False, "error": "All engines failed for segment regeneration.",
            "error_code": "ERR_REGEN_FAILED"}


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
