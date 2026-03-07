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
  1. Full TTSEngine from web app (normalizer + grammar + G2P + prosody)
  2. edge-tts (Microsoft Edge neural voices — Marathi + Sanskrit via Hindi)
  3. gTTS + pydub speed/pitch post-processing  (primary standalone)
  4. gTTS bare fallback (no pydub)
"""

import sys
import os
import json
import argparse
import tempfile
import traceback
import time
import socket

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
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
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
            if not os.path.isfile(fpath):
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
# Edge-TTS (Microsoft Edge neural voices) — supports Marathi + Hindi (for Sanskrit)
# ---------------------------------------------------------------------------
_EDGE_VOICE_MAP = {
    # (language, gender) → edge-tts voice name
    ("mr", "female"): "mr-IN-AarohiNeural",
    ("mr", "male"):   "mr-IN-ManoharNeural",
    ("hi", "female"): "hi-IN-SwaraNeural",
    ("hi", "male"):   "hi-IN-MadhurNeural",
    # Sanskrit → Hindi voices (closest Devanagari match, better phonology than Marathi)
    ("sa", "female"): "hi-IN-SwaraNeural",
    ("sa", "male"):   "hi-IN-MadhurNeural",
    # Old Marathi → Marathi voices (phonetic preprocessing handles the rest)
    ("mr-old", "female"): "mr-IN-AarohiNeural",
    ("mr-old", "male"):   "mr-IN-ManoharNeural",
}

def _edge_tts_available() -> bool:
    """Check whether edge_tts is importable."""
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
        log.warning("[edge-tts] edge_tts package not installed")
        return {}

    voice = _EDGE_VOICE_MAP.get((language, gender))
    if voice is None:
        # Try same language with default gender, else fallback
        voice = _EDGE_VOICE_MAP.get((language, "female"))
    if voice is None:
        log.warning("[edge-tts] No voice mapping for lang=%s gender=%s", language, gender)
        return {}

    # edge-tts rate: "+0%", "-50%", "+100%" etc.
    rate_pct = int((speed - 1.0) * 100)
    rate_str = f"{rate_pct:+d}%"
    # edge-tts volume: "+0%", "-50%" etc.
    vol_pct = int((volume - 1.0) * 100)
    vol_str = f"{vol_pct:+d}%"
    # edge-tts pitch: "+0Hz", "-50Hz", "+100Hz" etc.
    pitch_hz = int((pitch - 1.0) * 100)
    pitch_str = f"{pitch_hz:+d}Hz"

    # Preprocess if verse mode or Old Marathi
    if language == "mr-old":
        # Old Marathi: always use Old Marathi preprocessing (Ovi metre etc.)
        if _phonetic_old_marathi is not None:
            processed = _phonetic_old_marathi(text)
        else:
            processed = apply_old_marathi_phonetics(text)
        processed = _apply_g2p(processed)
        log.info("[edge-tts] [Old Marathi] Preprocessed | orig=%d  new=%d chars", len(text), len(processed))
    elif is_verse:
        processed = _preprocess_stotra_text(text)
        processed = _apply_g2p(processed)
        log.info("[edge-tts] [Verse] Preprocessed | orig=%d  new=%d chars", len(text), len(processed))
    else:
        processed = _apply_g2p(text)

    log.info("[edge-tts] Generating | voice=%s rate=%s vol=%s pitch=%s text_len=%d",
             voice, rate_str, vol_str, pitch_str, len(processed))

    async def _run():
        comm = edge_tts.Communicate(
            text=processed,
            voice=voice,
            rate=rate_str,
            volume=vol_str,
            pitch=pitch_str,
        )
        await comm.save(output_path)

    t0 = time.time()
    try:
        # Use new event loop to avoid issues if one is already running
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:
        log.error("[edge-tts] Failed: %s", exc)
        log.debug("[edge-tts] Traceback:\n%s", traceback.format_exc())
        return {}

    # Verify file was created and has content
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        log.warning("[edge-tts] Output file missing or too small")
        try: os.unlink(output_path)
        except OSError: pass
        return {}

    elapsed = time.time() - t0
    engine_name = f"edge_tts_{language}"
    if is_verse:
        engine_name += "_verse"
    log.info("[edge-tts] SUCCESS -> %s (%.2fs) voice=%s", output_path, elapsed, voice)
    return {"success": True, "audio_path": output_path, "engine": engine_name,
            "elapsed_sec": round(elapsed, 2)}


# ---------------------------------------------------------------------------
# Prosody-segmented edge-tts (FEAT-8)
# ---------------------------------------------------------------------------

def _generate_edge_prosody(text, language, gender, speed, pitch, volume,
                           output_path):
    """Generate edge-tts audio with prosody-segmented pauses.

    Uses ProsodyEngine to determine natural pause points, generates
    per-segment audio via edge-tts neural voice, and stitches with
    calibrated pydub silence.  Only used for prose (not verse).

    Edge-tts natively handles speed/pitch/volume via SSML, so no pydub
    post-processing is needed for those parameters.

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

            # Per-segment pitch adjustment from ProsodyEngine emphasis
            seg_pitch_hz = base_pitch_hz + int(seg.pitch_shift * 100)
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
                                  output_path):
    """Generate edge-tts audio with verse-specific prosody segmentation.

    Uses ProsodyEngine for metre-aware verse segmentation (pauses at ।/॥,
    pitch contour, tts_rate per metre), generates per-segment audio via
    edge-tts neural voice, and stitches with calibrated verse pauses for
    natural shloka recitation.

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

            # Per-segment rate from ProsodyEngine (verse metre rate × user speed)
            seg_rate = speed * seg.tts_rate if seg.tts_rate else speed
            rate_str = f"{int((seg_rate - 1.0) * 100):+d}%"

            # Per-segment pitch: user pitch + ProsodyEngine contour
            seg_pitch_hz = base_pitch_hz + int(seg.pitch_shift * 100)
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
# Stotra Library — pre-recorded audio for known stotras
# ---------------------------------------------------------------------------
_stotra_catalog = None

def _load_stotra_catalog():
    """Load stotra_catalog.json from STOTRA_DIR. Returns dict or empty."""
    global _stotra_catalog
    if _stotra_catalog is not None:
        return _stotra_catalog
    stotra_dir = os.environ.get("STOTRA_AUDIO_DIR", "")
    if not stotra_dir or not os.path.isdir(stotra_dir):
        _stotra_catalog = {}
        return _stotra_catalog
    catalog_path = os.path.join(stotra_dir, "stotra_catalog.json")
    if not os.path.isfile(catalog_path):
        log.debug("No stotra_catalog.json in %s", stotra_dir)
        _stotra_catalog = {}
        return _stotra_catalog
    try:
        with open(catalog_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Index by fingerprints for fast lookup
        catalog = {}
        for entry in data.get("stotras", []):
            for fp in entry.get("fingerprints", []):
                catalog[fp] = entry
        _stotra_catalog = catalog
        log.info("Stotra catalog loaded | %d entries, %d fingerprints from %s",
                 len(data.get('stotras', [])), len(catalog), stotra_dir)
        return _stotra_catalog
    except Exception as exc:
        log.warning("Failed to load stotra catalog: %s", exc)
        _stotra_catalog = {}
        return _stotra_catalog


def _fingerprint(text: str) -> str:
    """Generate a simple fingerprint from Devanagari text for stotra matching.
    Strips whitespace, digits, punctuation, dandas and takes first 60 Devanagari chars."""
    import re
    # Keep only Devanagari letters and matras (U+0900-U+0963, U+0970-U+097F)
    # Exclude dandas (।॥ = U+0964-U+0965) and Devanagari digits (U+0966-U+096F)
    cleaned = re.sub(r'[^\u0900-\u0963\u0970-\u097F]', '', text)
    return cleaned[:60]


def _try_stotra_library(text: str, speed: float, pitch: float, volume: float,
                         output_path: str) -> dict:
    """Check if text matches a known stotra; if so, copy/adjust pre-recorded audio."""
    catalog = _load_stotra_catalog()
    if not catalog:
        return {}
    fp = _fingerprint(text)
    if not fp or len(fp) < 20:
        return {}
    # Try exact match first, then prefix match (catalog key starts with fp or vice versa)
    entry = catalog.get(fp)
    if entry is None:
        for key, val in catalog.items():
            if key.startswith(fp) or fp.startswith(key):
                entry = val
                break
    if entry is None:
        return {}
    stotra_dir = os.environ.get("STOTRA_AUDIO_DIR", "")
    audio_file = os.path.join(stotra_dir, entry.get("audio_file", ""))
    if not os.path.isfile(audio_file):
        log.warning("[Stotra Library] Audio file not found: %s", audio_file)
        return {}
    log.info("[Stotra Library] MATCH: %s -> %s", entry.get("name", "unknown"), audio_file)
    import shutil
    # Apply speed/volume if needed via pydub, else copy directly
    needs_fx = (abs(speed - 1.0) > 0.05 or abs(pitch - 1.0) > 0.05 or
                abs(volume - 1.0) > 0.05)
    if needs_fx:
        try:
            _apply_pitch_speed(audio_file, speed, pitch, volume, output_path)
        except Exception:
            shutil.copy(audio_file, output_path)
    else:
        shutil.copy(audio_file, output_path)
    return {"success": True, "audio_path": output_path,
            "engine": "stotra_library",
            "stotra_name": entry.get("name", ""),
            "stotra_source": entry.get("source", "")}


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
    """Apply pronunciation and pause rules for stotra/shloka Sanskrit-Marathi text.

    If the full phonetic module is available, delegates to it.
    Otherwise falls back to the inline rules below.

    Sanskrit has strict phonetic rules that gTTS (a Marathi conversational model)
    cannot handle natively.  This function rewrites the text so that gTTS produces
    approximately correct pronunciation.

    1.  STRUCTURAL cleanup (hyphens, verse numbers, dandas → punctuation)
    2.  TERMINAL HALANT expansion (म् → म, न् → न, etc.)
    3.  VISARGA context-dependent expansion (ः → हा / ह / स / श)
    4.  Echoing terminal visarga (-iḥ → -ihi, -uḥ → -uhu)
    5.  ANUSVARA context-dependent nasal hint
    6.  CONJUNCT pronunciation hints for gTTS
    7.  OM / special symbols
    8.  Final punctuation & whitespace cleanup
    """
    # Use the full phonetic module if available
    if _phonetic_stotra is not None:
        return _phonetic_stotra(text)

    # --- Fallback: inline rules (kept for environments without the module) ---
    import re
    r = text

    # ── 0. Unicode NFC ─────────────────────────────────────────────────
    import unicodedata
    r = unicodedata.normalize('NFC', r)

    # ── 1. STRUCTURAL CLEANUP ──────────────────────────────────────────
    # Remove hyphens inside compound words (वामाङ्कारूढ-सीता → वामाङ्कारूढसीता)
    r = re.sub(r'(?<=[\u0900-\u097F])-(?=[\u0900-\u097F])', '', r)
    # Remove ZWJ/ZWNJ that confuse tokenizers
    r = r.replace('\u200D', '').replace('\u200C', '')

    # ── 2. VERSE STRUCTURE → PUNCTUATION ───────────────────────────────
    # Section headers: ॥ अथ ध्यानम् ॥ → keep text, add period
    r = re.sub(r'॥\s*[\d०-९]+\s*॥', '.', r)  # verse numbers
    r = r.replace('॥', '.')
    r = r.replace('।', ',')
    r = re.sub(r'\n\s*\n+', '\n.\n', r)       # stanza breaks

    # ── 3. ASCII COLON → VISARGA ───────────────────────────────────────
    r = re.sub(r'([\u0900-\u097F]):', r'\1ः', r)

    # ── 4. TERMINAL HALANT (विराम) ─────────────────────────────────────
    # Sanskrit words ending in halant+consonant: gTTS cannot pronounce these.
    # Add implicit short 'a' (schwa) so gTTS enunciates the final consonant.
    # म् → म, न् → न, त् → त, etc.  (before space, punct, or end of string)
    HALANT = '\u094D'
    r = re.sub(HALANT + r'(?=[\s.,;!?\n]|$)', '', r)

    # ── 5. VISARGA (ः) — context-dependent ─────────────────────────────
    # Before palatal consonants (च, छ, ज, झ, श): ः → श
    r = re.sub(r'ः(?=[चछजझश])', 'श', r)
    # Before retroflex consonants (ट, ठ, ड, ढ, ष): ः → ष
    r = re.sub(r'ः(?=[टठडढष])', 'ष', r)
    # Before dental/sibilant consonants (त, थ, द, ध, स, न): ः → स
    r = re.sub(r'ः(?=[तथदधसन])', 'स', r)
    # Terminal visarga (before space/punct/newline/end): ः → हा
    r = re.sub(r'ः(?=[\s.,\n]|$)', 'हा', r)
    # Remaining mid-word visarga: ः → ह
    r = r.replace('ः', 'ह')

    # ── 6. ANUSVARA (ं) pronunciation hints ────────────────────────────
    # Before velar (क,ख,ग,घ): anusvara sounds like ङ — leave as ं (gTTS OK)
    # Before palatal (च,छ,ज,झ): anusvara → ञ-like — leave as ं
    # Before labial (प,फ,ब,भ,म): anusvara → म-like — leave as ं
    # anusvara before nothing or non-Devanagari: nasalization — leave as ं
    # gTTS handles anusvara reasonably, so minimal intervention here.

    # ── 7. CONJUNCT pronunciation aids for gTTS ────────────────────────
    # ज्ञ is commonly mispronounced — hint as द्न्य (Marathi) or ग्य (Sanskrit)
    r = r.replace('ज्ञ', 'द्न्य')
    # ऋ vowel — gTTS often says 'ri' weakly; reinforce
    r = r.replace('ॠ', 'री')   # long ṝ
    # क्ष → ksha — gTTS usually handles this, leave as is

    # ── 8. SPECIAL SYMBOLS ─────────────────────────────────────────────
    r = r.replace('ॐ', 'ओम')

    # ── 9. CLEANUP ─────────────────────────────────────────────────────
    r = re.sub(r'[.,]{2,}', '.', r)         # collapse repeated punctuation
    r = re.sub(r'^\s*[.,]\s*', '', r)       # strip leading punctuation
    r = re.sub(r'[ \t]+', ' ', r)           # normalise whitespace
    r = re.sub(r'\n{3,}', '\n\n', r)
    return r.strip()


# ---------------------------------------------------------------------------
# Prose text preprocessing (non-verse Marathi book/document text)
# ---------------------------------------------------------------------------

# ── Honorific / common abbreviation expansions ──────────────────────────────
# Ordered longest-first so sub-patterns don't shadow longer ones.
_MARATHI_ABBREV = [
    # Honorifics (most common in religious/biographical Marathi)
    (r'\bप\s*\.\s*पू\s*\.', 'परमपूज्य'),
    (r'\bपू\s*\.', 'पूज्य'),
    (r'\bश्री\s*\.', 'श्री'),
    (r'\bश्रीमती\s*\.', 'श्रीमती'),
    (r'\bसौ\s*\.', 'सौभाग्यवती'),
    (r'\bकु\s*\.', 'कुमारी'),
    (r'\bडॉ\s*\.', 'डॉक्टर'),
    (r'\bप्रा\s*\.', 'प्राध्यापक'),
    (r'\bप्रो\s*\.', 'प्रोफेसर'),
    (r'\bस्व\s*\.', 'स्वर्गीय'),
    # Measures / misc
    (r'\bकि\s*\.\s*मी\s*\.', 'किलोमीटर'),
    (r'\bकि\s*\.', 'किलो'),
    (r'\bनं\s*\.', 'नंबर'),
    (r'\bक्र\s*\.', 'क्रमांक'),
    (r'\bरु\s*\.', 'रुपये'),
    (r'\bइ\s*\.\s*स\s*\.', 'इसवी सन'),
    (r'\bइ\s*\.', 'इत्यादी'),
]

# ── English → Devanagari common word lookup ──────────────────────────────────
_ENGLISH_TO_DEVNAGARI = {
    # Medical
    'heart'       : 'हार्ट',
    'attack'      : 'अटॅक',
    'normal'      : 'नॉर्मल',
    'abnormal'    : 'अबनॉर्मल',
    'delivery'    : 'डिलिव्हरी',
    'convulsion'  : 'कन्व्हल्शन',
    'convulsions' : 'कन्व्हल्शन्स',
    'injection'   : 'इंजेक्शन',
    'injections'  : 'इंजेक्शन्स',
    'doctor'      : 'डॉक्टर',
    'doctors'     : 'डॉक्टर्स',
    'hospital'    : 'हॉस्पिटल',
    'tablet'      : 'टॅब्लेट',
    'tablets'     : 'टॅब्लेट्स',
    'blood'       : 'ब्लड',
    'pressure'    : 'प्रेशर',
    'operation'   : 'ऑपरेशन',
    'patient'     : 'पेशंट',
    'cesarean'    : 'सिझेरियन',
    'caesarean'   : 'सिझेरियन',
    'misoprost'   : 'मिसोप्रोस्ट',
    'expand'      : 'एक्सपँड',
    'expanding'   : 'एक्सपँडिंग',
    # Everyday
    'station'     : 'स्टेशन',
    'bus'         : 'बस',
    'train'       : 'ट्रेन',
    'office'      : 'ऑफिस',
    'school'      : 'स्कूल',
    'college'     : 'कॉलेज',
    'mobile'      : 'मोबाईल',
    'phone'       : 'फोन',
    'call'        : 'कॉल',
    'online'      : 'ऑनलाईन',
    'video'       : 'व्हिडिओ',
    'news'        : 'न्यूज',
    'test'        : 'टेस्ट',
    'report'      : 'रिपोर्ट',
    'god'         : 'गॉड',
    'sir'         : 'सर',
    'madam'       : 'मॅडम',
}


def _transliterate_english_char_level(word: str) -> str:
    """Letter-by-letter English → Devanagari fallback for unknown words.

    Maps English characters to approximate Marathi phonetics so the Marathi
    TTS voice reads them without switching to an English tone.
    """
    # Vowels: standalone (word-initial or after another vowel) vs. after consonant (matra form)
    _VOW_INIT  = {'a': 'अ', 'e': 'ए', 'i': 'इ', 'o': 'ओ', 'u': 'उ', 'y': 'य'}
    _VOW_MATRA = {'a': 'ा', 'e': 'े', 'i': 'ि', 'o': 'ो', 'u': 'ु', 'y': 'ी'}
    _CONS = {
        'b': 'ब', 'c': 'क', 'd': 'ड', 'f': 'फ', 'g': 'ग', 'h': 'ह',
        'j': 'ज', 'k': 'क', 'l': 'ल', 'm': 'म', 'n': 'न', 'p': 'प',
        'q': 'क', 'r': 'र', 's': 'स', 't': 'ट', 'v': 'व', 'w': 'व',
        'x': 'क्स', 'y': 'य', 'z': 'झ',
    }
    w = word.lower()
    out = []
    i = 0
    prev_was_cons = False
    while i < len(w):
        ch = w[i]
        # Skip silent final 'e'
        if ch == 'e' and i == len(w) - 1 and prev_was_cons:
            i += 1
            continue
        if ch in _VOW_INIT:
            out.append(_VOW_MATRA[ch] if prev_was_cons else _VOW_INIT[ch])
            prev_was_cons = False
        elif ch in _CONS:
            out.append(_CONS[ch])
            prev_was_cons = True
        # else: skip unknown characters (digits, punct kept outside)
        i += 1
    return ''.join(out) if out else word


def _transliterate_english_words(text: str) -> str:
    """Replace ASCII English words embedded in Devanagari text with Devanagari phonetics.

    Only targets words that are purely ASCII alphabetic (no digits, no URLs).
    Short words ≤ 2 chars (prepositions like 'a', 'of') are left as-is since
    gTTS usually reads them acceptably and they're often OCR artefacts anyway.
    """
    import re

    def replace_word(m: 're.Match') -> str:
        w = m.group(0)
        if len(w) <= 2:
            return w  # leave short words
        key = w.lower()
        if key in _ENGLISH_TO_DEVNAGARI:
            return _ENGLISH_TO_DEVNAGARI[key]
        return _transliterate_english_char_level(w)

    # Match runs of ASCII letters only (not digits, not URLs)
    return re.sub(r'[A-Za-z]{3,}', replace_word, text)


def _preprocess_prose_text(text: str) -> str:
    """Preprocess Marathi prose (book/document) text for natural TTS reading.

    Applied before every TTS engine for non-verse book text:

    1.  Expand honorific abbreviations: प. पू. → परमपूज्य, श्री. → श्री, etc.
    2.  Remove mid-sentence pauses caused by abbreviation periods:
        a single Devanagari word (≤4 chars) followed by '.' followed by
        more text is an abbreviation, not a sentence end — remove the period
        so gTTS doesn't pause there.
    3.  Transliterate embedded English words to Devanagari phonetics so the
        Marathi TTS voice doesn't switch to an English accent.
    """
    import re
    import unicodedata
    r = unicodedata.normalize('NFC', text)

    # ── 1. Honorific / abbreviation expansion ───────────────────────────
    for pattern, repl in _MARATHI_ABBREV:
        r = re.sub(pattern, repl, r)

    # ── 2. Remove pause-causing periods from remaining abbreviations ─────
    # Only target genuinely short words (word-boundary + 1-2 Devanagari chars + period)
    # that are followed by a space and more Devanagari — these are abbreviations.
    # Deliberately conservative: 3+ char words keep their sentence-ending period.
    # e.g. "मो. ९८..." → "मो ९८"    "kā. sā." type abbreviated honorifics → removed
    r = re.sub(
        r'(?<!\S)([\u0900-\u097F]{1,2})\.'
        r'(?=\s+[\u0900-\u097F\u0966-\u096F])',
        r'\1',
        r
    )

    # ── 3. English word transliteration ─────────────────────────────────
    r = _transliterate_english_words(r)

    # ── 4. Cleanup ───────────────────────────────────────────────────────
    r = re.sub(r'[ \t]+', ' ', r)
    return r.strip()


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


def _generate_verse_audio(text: str, speed: float, pitch: float, volume: float,
                          output_path: str, language: str = "mr",
                          original_language: str = "mr") -> dict:
    """Generate TTS audio with verse/shloka treatment.

    Uses ``original_language`` to choose the correct phonetic preprocessing:
    - ``sa``     → apply_sanskrit_phonetics (ज्ञ kept, visarga sandhi, etc.)
    - ``mr-old`` → apply_old_marathi_phonetics (no schwa deletion)
    - ``mr``     → _preprocess_stotra_text (Sanskrit rules + structural cleanup)
    ``language`` is the already-mapped gTTS language code (e.g. ``hi`` for Sanskrit).
    """
    try:
        from gtts import gTTS  # type: ignore
    except ImportError as exc:
        log.warning("gTTS not available for verse mode: %s", exc)
        return {}   # empty → caller falls back to bare gTTS

    # Stage A: stotra-specific preprocessing — pick rules by original language.
    # Sanskrit: _preprocess_stotra_text already calls apply_sanskrit_phonetics internally.
    #   Call it directly — no separate apply_sanskrit_phonetics call needed.
    # Old Marathi: apply old-Marathi phonetics first (no schwa deletion), then structural cleanup.
    # Modern Marathi / default: full stotra preprocessing.
    if original_language == "sa":
        preprocessed = _preprocess_stotra_text(text)
    elif original_language == "mr-old":
        preprocessed = _preprocess_stotra_text(apply_old_marathi_phonetics(text))
    else:
        preprocessed = _preprocess_stotra_text(text)
    # Stage B: full G2P pipeline (conjuncts, anusvara, schwa etc.)
    preprocessed = _apply_g2p(preprocessed)
    # Apply gTTS-specific fixes (ZWNJ for y-glide, terminal halant)
    # AFTER G2P because G2P strips ZWNJ.
    if gtts_language == 'mr':
        preprocessed = apply_gtts_mr_fixes(preprocessed)
    log.info("[Verse] Preprocessed stotra text | orig=%d  new=%d chars", len(text), len(preprocessed))
    log.debug("[Verse] Preview: %.400s", preprocessed)

    if not preprocessed.strip():
        log.warning("[Verse] Preprocessed text is empty")
        return {}

    # Only use gTTS slow mode for very low speeds (it is *extremely* slow)
    use_slow = speed < 0.75

    fd, raw = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
    os.close(fd)

    t0 = time.time()
    try:
        gTTS(text=preprocessed, lang=language, slow=use_slow, lang_check=False).save(raw)
    except Exception as exc:
        log.error("[Verse] gTTS failed: %s", exc)
        try: os.unlink(raw)
        except OSError: pass
        return {}

    log.info("[Verse] gTTS saved in %.2fs (slow=%s)", time.time() - t0, use_slow)

    # Optionally apply effects if pydub + ffmpeg are available
    import shutil
    needs_fx = (abs(speed - 1.0) > 0.05 or abs(pitch - 1.0) > 0.05 or
                abs(volume - 1.0) > 0.05)
    if needs_fx:
        try:
            _apply_pitch_speed(raw, speed, pitch, volume, output_path)
            try: os.unlink(raw)
            except OSError: pass
        except Exception as exc:
            log.warning("[Verse] pydub effects skipped (%s) — using raw gTTS output", exc)
            shutil.move(raw, output_path)
    else:
        shutil.move(raw, output_path)

    elapsed = time.time() - t0
    log.info("[Verse] SUCCESS -> %s (%.2fs)", output_path, elapsed)
    return {"success": True, "audio_path": output_path, "engine": "gtts_verse",
            "elapsed_sec": round(elapsed, 2)}


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

# gTTS-supported Devanagari languages → fallback mapping for unsupported ones.
# Sanskrit (sa) → Hindi: same Devanagari script, phonologically much closer than Marathi.
# Old Marathi → Marathi (same script, different phonology handled by preprocessing).
_GTTS_LANG_MAP = {
    "sa": "hi",      # Sanskrit → Hindi (phonologically closest available)
    "mr-old": "mr",  # Old Marathi → Marathi (same script)
    "ne": "hi",      # Nepali  → Hindi   (same script, close phonology)
}


def generate_tts(text: str,
                 speed: float = 1.0,
                 pitch: float = 1.0,
                 volume: float = 1.0,
                 output_path: str = None,
                 emotion: str = None,
                 is_verse: bool = False,
                 language: str = "mr",
                 engine: str = "auto",
                 gender: str = "female") -> dict:
    """Generate Marathi TTS audio. Returns {success, audio_path} or {success:False, error}."""
    t0 = time.time()

    # Preserve the *original* language for edge-tts (which has its own voice map).
    # gTTS fallback mapping (sa→mr) is applied only when we actually reach gTTS.
    gtts_language = _GTTS_LANG_MAP.get(language, language)

    log.info("=== generate_tts START | text_len=%d speed=%.2f pitch=%.2f "
             "volume=%.2f emotion=%s verse=%s lang=%s engine=%s gender=%s ===",
             len(text), speed, pitch, volume, emotion, is_verse, language, engine, gender)
    log.debug("Input text preview: %.200s", text)

    # Store original pitch for edge-tts (which has native male/female voices).
    # gTTS is female-only, so male voice needs pitch down ~4 semitones (factor ~0.79).
    original_pitch = pitch
    gtts_pitch = pitch
    if gender == 'male':
        gtts_pitch = pitch * 0.79 if abs(pitch - 1.0) > 0.01 else 0.79
        log.info("[Gender] Male voice: gTTS pitch=%.2f, edge-tts pitch=%.2f (native male voice)",
                 gtts_pitch, original_pitch)

    if not text or not text.strip():
        log.error("Empty input text")
        return {"success": False, "error": "Empty text",
                "error_code": "ERR_EMPTY_TEXT", "stage": "validation"}

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)

    # ── Prose preprocessing (non-verse Marathi book/document text) ────────
    # Applied before ALL engines.  Expands "प. पू." → "परमपूज्य", removes
    # spurious abbreviation pauses, and transliterates embedded English words
    # so the Marathi TTS voice doesn't switch accent mid-sentence.
    # Verse text gets its own stotra preprocessing inside _generate_verse_audio.
    if not is_verse:
        preprocessed_text = _preprocess_prose_text(text)
        if preprocessed_text != text:
            log.info("[Prose] Preprocessed | orig=%d new=%d chars", len(text), len(preprocessed_text))
            log.debug("[Prose] Preview: %.300s", preprocessed_text)
        text = preprocessed_text

    # ── Grammar engine (FEAT-3) — spelling, sandhi, vibhakti, punctuation ──
    # Applied to Marathi prose only (not Sanskrit, not verse).
    if not is_verse and language not in ("sa", "en"):
        grammar_text = _apply_grammar(text)
        if grammar_text != text:
            log.info("[Grammar] Applied | orig=%d new=%d chars",
                     len(text), len(grammar_text))
        text = grammar_text

    # ── Custom Voice Engine (FEAT-50) ────────────────────────────────────
    # Highest priority: try pre-recorded segment library and custom ONNX
    # model BEFORE any network-dependent engine.  Works offline.
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

    # Stage 0: Stotra library — pre-recorded audio for known stotras/mantras
    if is_verse:
        log.info("[Stage 0] Checking stotra library")
        try:
            result = _try_stotra_library(text, speed, pitch, volume, output_path)
            if result.get("success"):
                result["elapsed_sec"] = round(time.time() - t0, 2)
                log.info("[Stage 0] Stotra library HIT: %s (%.2fs)",
                         result.get('stotra_name', ''), result['elapsed_sec'])
                return result
            log.info("[Stage 0] No stotra match, proceeding to synthesis")
        except Exception as exc:
            log.warning("[Stage 0] Stotra library error: %s", exc)

    # Stage 1: Full TTSEngine from web app
    log.info("[Stage 1] Attempting full TTSEngine")
    try:
        from tts.utils.core.tts_engine import TTSEngine  # type: ignore
        engine = TTSEngine()
        log.info("[Stage 1] TTSEngine loaded OK")
        voice_params = {"speed": speed, "pitch": pitch, "volume": volume}
        if emotion:
            voice_params["emotion"] = emotion
        processed = engine.preprocess_verse_text(text) if is_verse \
            else engine.preprocess_marathi_text(text)
        log.debug("[Stage 1] Preprocessed: %.200s", processed)
        audio = engine.generate_tts_audio(text=processed, voice_params=voice_params)
        if audio and os.path.exists(audio):
            if audio != output_path:
                import shutil
                shutil.move(audio, output_path)
            elapsed = time.time() - t0
            log.info("[Stage 1] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
            return {"success": True, "audio_path": output_path, "engine": "full_tts_engine",
                    "elapsed_sec": round(elapsed, 2)}
        log.warning("[Stage 1] Engine returned no audio path")
    except ImportError:
        log.info("[Stage 1] TTSEngine not available (web app not on Python path)")
    except Exception as exc:
        log.warning("[Stage 1] TTSEngine failed: %s", exc)
        log.debug(traceback.format_exc())

    # ── Network pre-check (BUG-21) ───────────────────────────────────────
    # Stages 2+ (edge-tts, gTTS) require internet.  Fail fast with a clear
    # message instead of waiting 30 s for a socket timeout.
    if not _is_network_available():
        log.error("[Network] No internet connectivity — cannot reach TTS API")
        return {"success": False,
                "error": "No internet connection. Please check your network and try again.",
                "error_code": "ERR_NO_NETWORK",
                "stage": "network_check"}

    # Stage 2: edge-tts (Microsoft Edge neural voices)
    # Supports Marathi natively and Sanskrit via Hindi voice (same Devanagari script)
    if _edge_tts_available():
        log.info("[Stage 2] Attempting edge-tts | lang=%s gender=%s verse=%s", language, gender, is_verse)
        # Try prosody-segmented edge-tts first
        if is_verse:
            # Verse-specific prosody with metre-aware pauses & pitch contour
            try:
                prosody_result = _generate_edge_verse_prosody(
                    text, language, gender, speed, original_pitch, volume,
                    output_path)
                if prosody_result and prosody_result.get("success"):
                    prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
                    log.info("[Stage 2] edge-tts verse prosody SUCCESS "
                             "(%d segments, %.2fs)",
                             prosody_result.get("segments", 0),
                             prosody_result["elapsed_sec"])
                    return prosody_result
            except Exception as exc:
                log.warning("[Stage 2] edge-tts verse prosody failed: %s", exc)
                log.debug(traceback.format_exc())
        else:
            # Prose prosody (FEAT-8)
            try:
                prosody_result = _generate_edge_prosody(
                    text, language, gender, speed, original_pitch, volume,
                    output_path)
                if prosody_result and prosody_result.get("success"):
                    prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
                    log.info("[Stage 2] edge-tts prosody SUCCESS (%d segments, %.2fs)",
                             prosody_result.get("segments", 0),
                             prosody_result["elapsed_sec"])
                    return prosody_result
            except Exception as exc:
                log.warning("[Stage 2] edge-tts prosody failed: %s", exc)
                log.debug(traceback.format_exc())
        # Single-call edge-tts (fallback)
        try:
            result = _generate_edge_tts(
                text, language, gender, speed, original_pitch, volume,
                output_path, is_verse=is_verse,
            )
            if result.get("success"):
                result["elapsed_sec"] = round(time.time() - t0, 2)
                log.info("[Stage 2] edge-tts SUCCESS (%.2fs) engine=%s",
                         result["elapsed_sec"], result.get("engine"))
                return result
            log.info("[Stage 2] edge-tts returned empty, falling through to gTTS")
        except Exception as exc:
            log.warning("[Stage 2] edge-tts failed: %s", exc)
            log.debug(traceback.format_exc())
    else:
        log.info("[Stage 2] edge-tts not installed, skipping")

    # For gTTS stages, map unsupported languages (sa→mr) since gTTS has no Sanskrit
    if gtts_language != language:
        log.info("[Lang] Mapped '%s' → '%s' for gTTS fallback", language, gtts_language)

    # Stage 3: gTTS + pydub
    log.info("[Stage 3] gTTS + pydub effects | verse=%s", is_verse)

    # 3a: Verse/shloka mode — stotra preprocessing + single gTTS call
    if is_verse:
        try:
            result = _generate_verse_audio(text, speed, gtts_pitch, volume, output_path,
                                           language=gtts_language,
                                           original_language=language)
            if result.get("success"):
                result["elapsed_sec"] = round(time.time() - t0, 2)
                log.info("[Stage 3a] Verse audio SUCCESS (%.2fs)", result["elapsed_sec"])
                return result
            log.info("[Stage 3a] Verse audio returned empty, falling through to normal gTTS")
        except Exception as exc:
            log.warning("[Stage 3a] Verse mode failed: %s", exc)
            log.debug(traceback.format_exc())

    # ── Prosody-segmented generation (FEAT-1) ────────────────────────────
    # For prose text, use ProsodyEngine to split at natural clause/sentence
    # boundaries, generate audio per segment, and stitch with calibrated
    # silence pauses.  Falls through to single-call if unavailable.
    if not is_verse:
        prosody_result = _generate_prosody_audio(
            text, speed, gtts_pitch, volume, output_path, language, gtts_language)
        if prosody_result and prosody_result.get("success"):
            prosody_result["elapsed_sec"] = round(time.time() - t0, 2)
            log.info("[Prosody] SUCCESS -> %s (%d segments, %.2fs)",
                     output_path, prosody_result.get("segments", 0),
                     prosody_result["elapsed_sec"])
            return prosody_result

    # 3b: Normal gTTS (with G2P) — fallback if prosody unavailable
    try:
        normalized = text if language == "sa" else _normalize_marathi(text)
        if language == "sa":
            normalized = apply_sanskrit_phonetics(normalized)
        elif language == "mr-old":
            normalized = apply_old_marathi_phonetics(normalized)
        else:
            normalized = apply_marathi_phonetics(normalized)  # Modern Marathi rules
        normalized = _apply_g2p(normalized)
        # Apply gTTS-specific fixes (ZWNJ for y-glide, terminal halant)
        # AFTER G2P because G2P strips ZWNJ.
        if gtts_language == 'mr':
            normalized = apply_gtts_mr_fixes(normalized)
        fd, raw = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)
        log.info("[Stage 3b] Calling gTTS | lang=%s text_len=%d slow=%s",
                 gtts_language, len(normalized), speed < 0.75)
        t_gtts = time.time()
        from gtts import gTTS  # type: ignore
        gTTS(text=normalized, lang=gtts_language, slow=(speed < 0.75), lang_check=False).save(raw)
        log.info("[Stage 3b] gTTS saved in %.2fs", time.time() - t_gtts)

        needs_fx = abs(speed-1.0)>0.05 or abs(gtts_pitch-1.0)>0.05 or abs(volume-1.0)>0.05
        if needs_fx:
            _apply_pitch_speed(raw, speed, gtts_pitch, volume, output_path)
            try: os.unlink(raw)
            except OSError: pass
        else:
            import shutil
            shutil.move(raw, output_path)

        elapsed = time.time() - t0
        log.info("[Stage 3b] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
        return {"success": True, "audio_path": output_path, "engine": "gtts_pydub",
                "elapsed_sec": round(elapsed, 2)}
    except Exception as exc:
        log.error("[Stage 3b] gTTS+pydub failed: %s\n%s", exc, traceback.format_exc())

    # Stage 4: Bare gTTS fallback
    log.info("[Stage 4] Bare gTTS fallback")
    try:
        from gtts import gTTS  # type: ignore
        gTTS(text=text, lang=gtts_language, slow=False, lang_check=False).save(output_path)
        elapsed = time.time() - t0
        log.info("[Stage 4] SUCCESS -> %s  (%.2fs)", output_path, elapsed)
        return {"success": True, "audio_path": output_path, "engine": "gtts_bare",
                "elapsed_sec": round(elapsed, 2)}
    except Exception as exc:
        log.error("[Stage 4] All TTS stages failed: %s\n%s", exc, traceback.format_exc())
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
                gtts_lang = _GTTS_LANG_MAP.get(language, language)
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
                    emotion: str = None) -> dict:
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
        for i, seg in enumerate(segments):
            result_segments.append({
                "index": i,
                "text": seg.text,
                "pause_after_ms": seg.pause_after_ms,
                "emotion": seg.emotion,
                "emphasis": round(seg.emphasis, 2),
                "pitch_shift": round(seg.pitch_shift, 2),
                "is_verse": seg.is_verse,
                "metre_name": seg.metre_name,
                "tts_rate": round(seg.tts_rate, 2),
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
    parser.add_argument("--text",   required=False, default=None)
    parser.add_argument("--text-file", default=None,
                        help="Read --text from a UTF-8 file (avoids CLI escaping issues)")
    parser.add_argument("--speed",  type=float, default=1.0)
    parser.add_argument("--pitch",  type=float, default=1.0)
    parser.add_argument("--volume", type=float, default=1.0)
    parser.add_argument("--output", default=None)
    parser.add_argument("--emotion", default=None)
    parser.add_argument("--lang",    default="mr",
                        help="Language code: mr, hi, sa, en")
    parser.add_argument("--engine",  default="auto",
                        help="TTS engine: auto, google, system")
    parser.add_argument("--gender",  default="female",
                        help="Voice gender: female, male")
    parser.add_argument("--verse",  action="store_true")
    parser.add_argument("--stotra-dir", default=None,
                        help="Directory containing stotra_catalog.json + audio files")
    args = parser.parse_args()
    if args.stotra_dir:
        os.environ["STOTRA_AUDIO_DIR"] = args.stotra_dir
    text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not text:
        print(json.dumps({"success": False, "error": "No --text or --text-file provided",
                          "error_code": "ERR_EMPTY_TEXT"}))
        sys.exit(1)
    result = generate_tts(text, args.speed, args.pitch, args.volume,
                          args.output, args.emotion, args.verse,
                          args.lang, args.engine, args.gender)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
