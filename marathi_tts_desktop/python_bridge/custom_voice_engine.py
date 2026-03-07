#!/usr/bin/env python3
"""
FEAT-50: Custom Stotra Voice Inference Engine

Provides two inference backends:
  1. Pre-recorded segment matching (Phase A) — immediate, perfect quality
  2. Piper ONNX model inference (Phase B) — trained custom voice

Phase A (segment library) works out-of-the-box with the preprocessed recordings.
Phase B activates when a trained .onnx model is present.

Usage from bridge:
    from custom_voice_engine import generate_custom_voice
    result = generate_custom_voice(text, speed, pitch, volume, output_path,
                                   is_verse=True, language="sa")
    # Returns {"success": True, "audio_path": ..., "engine": ...} or None
"""

import os
import sys
import json
import hashlib
import logging
import tempfile
import shutil
import re

log = logging.getLogger("custom_voice")

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
_BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))

# Model & segment directories — searched in order of priority
_MODEL_SEARCH_PATHS = [
    os.path.join(_BRIDGE_DIR, "models"),              # bridge-local
    os.path.join(_BRIDGE_DIR, "tts", "models"),       # under tts/
    os.path.join(_BRIDGE_DIR, "..", "models"),         # parent dir
]

_SEGMENT_SEARCH_PATHS = [
    os.path.join(_BRIDGE_DIR, "stotra_segments"),      # bridge-local
    os.path.join(_BRIDGE_DIR, "..", "data", "stotra_segments"),
]

_OUTPUT_DIR = os.path.join(_BRIDGE_DIR, "output")


# ---------------------------------------------------------------------------
# Phase A: Pre-recorded segment library
# ---------------------------------------------------------------------------
_segment_index = None   # lazy loaded


def _load_segment_index():
    """Load the segment index (alignment.json) from the first available path."""
    global _segment_index
    if _segment_index is not None:
        return _segment_index

    for base in _SEGMENT_SEARCH_PATHS:
        index_path = os.path.join(base, "alignment.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Build lookup: fingerprint -> segment info
                index = {}
                for entry in data.get("alignments", []):
                    text = entry.get("text", "")
                    fp = _fingerprint(text)
                    if fp:
                        index[fp] = {
                            "audio": os.path.join(base, entry.get("audio_file", "")),
                            "text": text,
                            "source": entry.get("source", ""),
                            "duration": entry.get("duration_sec", 0),
                        }
                _segment_index = index
                log.info("Segment library loaded: %d entries from %s",
                         len(index), base)
                return index
            except Exception as exc:
                log.warning("Failed to load segment index from %s: %s",
                            index_path, exc)

    _segment_index = {}
    return _segment_index


def _fingerprint(text: str) -> str:
    """Create a lookup fingerprint from Devanagari text.
    Keeps only Devanagari chars, strips whitespace/punctuation/digits/dandas."""
    if not text:
        return ""
    # Keep Unicode block 0900-097F (Devanagari)
    chars = [c for c in text if '\u0900' <= c <= '\u097F']
    clean = "".join(chars)[:80]  # first 80 Devanagari chars
    return clean


def _fingerprint_match(query_fp: str, index: dict, threshold: float = 0.6):
    """Find best matching segment by fingerprint overlap.
    Returns (key, score) or (None, 0)."""
    if not query_fp or not index:
        return None, 0

    best_key = None
    best_score = 0

    for key in index:
        # Compute overlap ratio
        if not key:
            continue
        shorter = min(len(query_fp), len(key))
        if shorter == 0:
            continue

        # Prefix match score
        match_len = 0
        for a, b in zip(query_fp, key):
            if a == b:
                match_len += 1
            else:
                break

        score = match_len / shorter
        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= threshold:
        return best_key, best_score
    return None, 0


def _try_segment_library(text: str, speed: float, pitch: float,
                         volume: float, output_path: str) -> dict:
    """Try to find a pre-recorded segment matching the input text.
    Returns result dict or empty dict on no match."""
    index = _load_segment_index()
    if not index:
        return {}

    fp = _fingerprint(text)
    if not fp:
        return {}

    # Try exact match first
    if fp in index:
        entry = index[fp]
        match_type = "exact"
    else:
        # Fuzzy prefix match
        key, score = _fingerprint_match(fp, index, threshold=0.7)
        if key is None:
            return {}
        entry = index[key]
        match_type = f"fuzzy({score:.2f})"

    audio_src = entry["audio"]
    if not os.path.exists(audio_src):
        log.warning("Segment audio not found: %s", audio_src)
        return {}

    # Copy/adjust audio to output
    needs_fx = (abs(speed - 1.0) > 0.05 or abs(pitch - 1.0) > 0.05
                or abs(volume - 1.0) > 0.05)

    if needs_fx:
        result_path = _apply_audio_effects(audio_src, speed, pitch, volume,
                                           output_path)
    else:
        shutil.copy2(audio_src, output_path)
        result_path = output_path

    if result_path and os.path.exists(result_path):
        log.info("Segment library HIT [%s]: %s (%.1fs)",
                 match_type, entry.get("source", ""), entry.get("duration", 0))
        return {
            "success": True,
            "audio_path": result_path,
            "engine": "custom_segment_library",
            "match_type": match_type,
            "source": entry.get("source", ""),
        }

    return {}


# ---------------------------------------------------------------------------
# Phase B: Piper ONNX model inference
# ---------------------------------------------------------------------------
_onnx_session = None
_onnx_config = None


def _find_onnx_model():
    """Find a trained .onnx model file in search paths."""
    for base in _MODEL_SEARCH_PATHS:
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.endswith(".onnx"):
                return os.path.join(base, name)
    return None


def _load_onnx_model():
    """Load ONNX model via onnxruntime. Returns session or None."""
    global _onnx_session, _onnx_config
    if _onnx_session is not None:
        return _onnx_session

    model_path = _find_onnx_model()
    if not model_path:
        log.info("No custom ONNX model found in search paths")
        return None

    # Look for config alongside model
    config_path = model_path.replace(".onnx", ".json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _onnx_config = json.load(f)
        except Exception:
            _onnx_config = {}

    try:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.inter_op_num_threads = 2
        opts.intra_op_num_threads = 2
        _onnx_session = ort.InferenceSession(model_path, opts)
        log.info("Custom ONNX model loaded: %s (%.1f MB)",
                 model_path, os.path.getsize(model_path) / (1024 * 1024))
        return _onnx_session
    except ImportError:
        log.info("onnxruntime not available — custom model disabled")
    except Exception as exc:
        log.warning("Failed to load ONNX model %s: %s", model_path, exc)

    return None


def _phonemize_text(text: str) -> list:
    """Convert Devanagari text to phoneme IDs for Piper VITS model."""
    try:
        from piper_phonemize import phonemize_espeak
        phonemes = phonemize_espeak(text, "hi")
        if phonemes:
            return phonemes[0]
    except ImportError:
        pass

    # Character-level fallback for Devanagari
    # Map each char to its Unicode codepoint offset from 0x0900
    ids = []
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            ids.append(cp - 0x0900 + 1)  # 1-indexed
        elif ch == ' ':
            ids.append(0)  # space token
    return ids


def _try_onnx_inference(text: str, speed: float, pitch: float,
                        volume: float, output_path: str) -> dict:
    """Generate audio using the trained ONNX model.
    Returns result dict or empty dict on failure."""
    session = _load_onnx_model()
    if session is None:
        return {}

    try:
        import numpy as np

        # Phonemize
        phoneme_ids = _phonemize_text(text)
        if not phoneme_ids:
            return {}

        # Prepare inputs (Piper VITS format)
        input_ids = np.array([phoneme_ids], dtype=np.int64)
        input_lengths = np.array([len(phoneme_ids)], dtype=np.int64)

        # Speed: length_scale (inverse — higher value = slower)
        length_scale = np.array([1.0 / max(speed, 0.1)], dtype=np.float32)
        noise_scale = np.array([0.667], dtype=np.float32)
        noise_scale_w = np.array([0.8], dtype=np.float32)

        # Run inference
        feeds = {
            "input": input_ids,
            "input_lengths": input_lengths,
            "scales": np.array([[noise_scale[0], length_scale[0],
                                 noise_scale_w[0]]], dtype=np.float32),
        }

        # Try matching input names from model
        input_names = [inp.name for inp in session.get_inputs()]
        actual_feeds = {}
        for name in input_names:
            if "input" in name and "length" not in name and "scale" not in name:
                actual_feeds[name] = input_ids
            elif "length" in name:
                actual_feeds[name] = input_lengths
            elif "scale" in name:
                actual_feeds[name] = feeds.get("scales",
                                               np.array([[0.667, 1.0, 0.8]],
                                                        dtype=np.float32))

        if not actual_feeds:
            actual_feeds = feeds

        outputs = session.run(None, actual_feeds)
        audio_data = outputs[0].squeeze()

        # Normalize to int16
        sample_rate = (_onnx_config or {}).get("audio", {}).get("sample_rate", 22050)
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Write WAV first
        import wave
        wav_path = output_path.replace(".mp3", ".wav")
        if wav_path == output_path:
            wav_path = output_path + ".wav"

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())

        # Convert to MP3 if possible
        final_path = output_path
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_wav(wav_path)

            # Apply pitch/volume
            if abs(pitch - 1.0) > 0.05:
                new_rate = int(audio_seg.frame_rate * pitch)
                audio_seg = audio_seg._spawn(audio_seg.raw_data,
                                             overrides={"frame_rate": new_rate})
                audio_seg = audio_seg.set_frame_rate(sample_rate)

            if abs(volume - 1.0) > 0.05:
                import math
                db_change = 20 * math.log10(max(volume, 0.01))
                audio_seg = audio_seg + db_change

            audio_seg.export(final_path, format="mp3")
        except ImportError:
            # No pydub — use WAV directly
            final_path = wav_path

        # Cleanup temp WAV
        if os.path.exists(wav_path) and wav_path != final_path:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

        if os.path.exists(final_path):
            log.info("ONNX inference SUCCESS: %s", final_path)
            return {
                "success": True,
                "audio_path": final_path,
                "engine": "custom_onnx_piper",
            }

    except Exception as exc:
        log.warning("ONNX inference failed: %s", exc)

    return {}


# ---------------------------------------------------------------------------
# Audio effects helper (shared by both phases)
# ---------------------------------------------------------------------------
def _apply_audio_effects(src: str, speed: float, pitch: float,
                         volume: float, dst: str) -> str:
    """Apply speed/pitch/volume adjustments to an audio file.
    Uses pydub if available, falls back to direct copy."""
    try:
        from pydub import AudioSegment
        import math

        audio = AudioSegment.from_file(src)
        sample_rate = audio.frame_rate

        # Pitch via frame-rate manipulation (safe range: 0.75-1.25)
        if abs(pitch - 1.0) > 0.05:
            clamped_pitch = max(0.75, min(1.25, pitch))
            new_rate = int(sample_rate * clamped_pitch)
            audio = audio._spawn(audio.raw_data,
                                 overrides={"frame_rate": new_rate})
            audio = audio.set_frame_rate(sample_rate)

        # Speed via frame-rate manipulation
        if abs(speed - 1.0) > 0.05:
            clamped_speed = max(0.75, min(1.25, speed))
            new_rate = int(audio.frame_rate * clamped_speed)
            audio = audio._spawn(audio.raw_data,
                                 overrides={"frame_rate": new_rate})
            audio = audio.set_frame_rate(sample_rate)

        # Volume in dB
        if abs(volume - 1.0) > 0.05:
            db = 20 * math.log10(max(volume, 0.01))
            audio = audio + db

        audio.export(dst, format="mp3")
        return dst

    except ImportError:
        shutil.copy2(src, dst)
        return dst
    except Exception as exc:
        log.warning("Audio effects failed: %s", exc)
        shutil.copy2(src, dst)
        return dst


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_custom_voice(text: str,
                          speed: float = 1.0,
                          pitch: float = 1.0,
                          volume: float = 1.0,
                          output_path: str = None,
                          is_verse: bool = False,
                          language: str = "mr") -> dict:
    """Try to generate audio using custom voice models/segments.

    Called by tts_bridge.py BEFORE the standard edge-tts/gTTS chain.
    Returns result dict with success=True on hit, or None to fall through.

    Priority:
      1. Pre-recorded segment library (exact/fuzzy match)
      2. ONNX custom voice model (if trained model available)
      3. None (fall through to standard engines)
    """
    if not text or not text.strip():
        return None

    if output_path is None:
        os.makedirs(_OUTPUT_DIR, exist_ok=True)
        fd, output_path = tempfile.mkstemp(suffix=".mp3", dir=_OUTPUT_DIR)
        os.close(fd)

    # Phase A: Try pre-recorded segments (verse content, known stotras)
    if is_verse:
        try:
            result = _try_segment_library(text, speed, pitch, volume, output_path)
            if result.get("success"):
                return result
        except Exception as exc:
            log.warning("Segment library error: %s", exc)

    # Phase B: Try ONNX model (works for any text)
    try:
        result = _try_onnx_inference(text, speed, pitch, volume, output_path)
        if result.get("success"):
            return result
    except Exception as exc:
        log.warning("ONNX inference error: %s", exc)

    return None


def is_custom_voice_available() -> bool:
    """Check if any custom voice source is available."""
    # Check segment library
    index = _load_segment_index()
    if index:
        return True
    # Check ONNX model
    if _find_onnx_model():
        return True
    return False
