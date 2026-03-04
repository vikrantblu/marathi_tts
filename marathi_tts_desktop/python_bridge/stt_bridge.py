#!/usr/bin/env python3
"""
STT Bridge - Marathi Speech-to-Text
=====================================
Transcribes audio files to Marathi text using OpenAI Whisper.

Usage:
    python stt_bridge.py transcribe --audio /path/to/audio.wav [--language mr]
    python stt_bridge.py record --duration 5 [--language mr] [--output /path/to/save.wav]

Returns: JSON { success, text, language, duration_seconds, segments, engine }
"""

import sys, os, json, argparse, traceback, time, tempfile

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

log = get_logger("stt_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

# Suppress noisy C++ / ML library logs
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

log.info("STT Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def transcribe(audio_path: str, language: str = "mr") -> dict:
    """Transcribe audio file to Marathi text.

    Returns: {success, text, language, duration_seconds, segments, engine}
    """
    t0 = time.time()
    log.info("=== transcribe START | audio=%s language=%s ===", audio_path, language)

    if not os.path.exists(audio_path):
        log.error("Audio file not found: %s", audio_path)
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    log.info("Audio file size: %d bytes", os.path.getsize(audio_path))

    # Stage 1: OpenAI Whisper
    log.info("[Stage 1] OpenAI Whisper")
    try:
        import whisper  # type: ignore
        log.info("[Stage 1] Loading whisper 'small' model")
        t_load = time.time()
        model = whisper.load_model("small")
        log.info("[Stage 1] Whisper model loaded in %.2fs", time.time() - t_load)

        log.info("[Stage 1] Transcribing...")
        t_transcribe = time.time()
        result = model.transcribe(audio_path, language=language, task="transcribe")
        elapsed_t = time.time() - t_transcribe
        log.info("[Stage 1] Transcription done in %.2fs", elapsed_t)

        text = result.get("text", "").strip()
        duration = result.get("duration", 0.0)
        segments = [
            {"start": round(s["start"], 2), "end": round(s["end"], 2),
             "text": s["text"].strip()}
            for s in result.get("segments", [])
        ]
        log.info("[Stage 1] SUCCESS | chars=%d duration=%.1fs elapsed=%.2fs",
                 len(text), duration, time.time() - t0)
        return {
            "success": True, "text": text,
            "language": result.get("language", language),
            "duration_seconds": round(duration, 2),
            "segments": segments, "engine": "whisper-small",
            "elapsed_sec": round(time.time() - t0, 2),
        }

    except ImportError:
        log.warning("[Stage 1] openai-whisper not installed. Run: pip install openai-whisper")
    except Exception as exc:
        log.error("[Stage 1] Whisper failed: %s\n%s", exc, traceback.format_exc())

    # Stage 2: Project speech_to_text module
    log.info("[Stage 2] Project speech_to_text module")
    try:
        sys.path.insert(0, _PROJECT_ROOT)
        from speech_to_text import transcribe as project_stt  # type: ignore
        text = project_stt(audio_path, language=language)
        log.info("[Stage 2] Project STT SUCCESS | chars=%d", len(text))
        return {"success": True, "text": text, "language": language,
                "segments": [], "engine": "project_stt",
                "elapsed_sec": round(time.time() - t0, 2)}
    except ImportError:
        log.warning("[Stage 2] speech_to_text module not found")
    except Exception as exc:
        log.error("[Stage 2] Project STT failed: %s", exc)

    log.error("All STT engines unavailable. Install whisper: pip install openai-whisper")
    return {
        "success": False,
        "error": "No STT engine available. Install: pip install openai-whisper",
    }


# ---------------------------------------------------------------------------
# Long-audio helpers (format conversion + chunking)
# ---------------------------------------------------------------------------

SUPPORTED_AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".ogg", ".flac",
                        ".opus", ".mp4", ".webm", ".wma"}
_CHUNK_SECONDS = 55  # safe margin below 60 s recognizer limit


def _ensure_wav(audio_path: str, tmp_dir: str) -> str:
    """Convert any audio file to 16 kHz mono WAV via pydub.
    Returns WAV path inside tmp_dir. Falls back to original path on failure.
    """
    ext = os.path.splitext(audio_path)[1].lower()
    wav_out = os.path.join(tmp_dir, "converted.wav")
    try:
        from pydub import AudioSegment  # type: ignore
        log.info("_ensure_wav: loading %s …", ext)
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_out, format="wav")
        log.info("_ensure_wav: %s → %s (%d ms)", ext, wav_out, len(audio))
        return wav_out
    except ImportError:
        log.warning("pydub not installed — audio conversion skipped. "
                    "Run: pip install pydub")
        return audio_path
    except Exception as exc:
        log.error("_ensure_wav failed: %s", exc)
        return audio_path


def _audio_duration_sec(audio_path: str) -> float:
    """Return approximate audio duration in seconds, or 0.0 on error."""
    try:
        from pydub import AudioSegment  # type: ignore
        return len(AudioSegment.from_file(audio_path)) / 1000.0
    except Exception:
        return 0.0


def _split_wav_chunks(wav_path: str, chunk_sec: int = _CHUNK_SECONDS) -> tuple:
    """Split WAV into fixed-size chunks.
    Returns (tmp_dir: str, chunk_paths: list). Caller must clean up tmp_dir.
    """
    tmp_dir = tempfile.mkdtemp(prefix="stt_chunks_")
    try:
        from pydub import AudioSegment  # type: ignore
        audio = AudioSegment.from_wav(wav_path)
        chunk_ms = chunk_sec * 1000
        paths = []
        for i, start in enumerate(range(0, len(audio), chunk_ms)):
            chunk = audio[start: start + chunk_ms]
            p = os.path.join(tmp_dir, f"chunk_{i:03d}.wav")
            chunk.export(p, format="wav")
            paths.append(p)
        log.info("_split_wav_chunks: %d chunks from %.1fs audio",
                 len(paths), len(audio) / 1000.0)
        return tmp_dir, paths
    except ImportError:
        log.warning("pydub not installed — chunking skipped")
        return tmp_dir, [wav_path]
    except Exception as exc:
        log.error("_split_wav_chunks failed: %s", exc)
        return tmp_dir, [wav_path]


def transcribe_long_audio(audio_path: str, language: str = "mr") -> dict:
    """Transcribe any-length audio with automatic format conversion + chunking.

    Strategy:
    - Convert non-WAV formats to 16 kHz mono WAV via pydub (mp3/m4a/aac/ogg/…).
    - Stage 1: Whisper 'small' — handles long audio natively, returns segments.
    - Stage 2 fallback: split into _CHUNK_SECONDS chunks → transcribe each via
      project speech_to_text module → join results.

    Returns same dict as transcribe() plus:
      chunk_count   (int) — 1 when Whisper used, N when chunked
      failed_chunks (int) — chunks that errored
    """
    t0 = time.time()
    log.info("=== transcribe_long_audio START | audio=%s language=%s ===",
             audio_path, language)

    if not os.path.exists(audio_path):
        log.error("File not found: %s", audio_path)
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    ext = os.path.splitext(audio_path)[1].lower()
    log.info("File ext=%s  size=%d bytes", ext, os.path.getsize(audio_path))

    tmp_conv = tempfile.mkdtemp(prefix="stt_conv_")
    try:
        wav_path = _ensure_wav(audio_path, tmp_conv) if ext != ".wav" else audio_path

        # ── Stage 1: Whisper (natively handles long audio) ──────────────────
        try:
            import whisper  # type: ignore
            log.info("[Long/S1] Loading whisper 'small' …")
            model = whisper.load_model("small")
            log.info("[Long/S1] Transcribing …")
            result = model.transcribe(wav_path, language=language, task="transcribe")
            text = result.get("text", "").strip()
            duration = result.get("duration", 0.0)
            segments = [
                {"start": round(s["start"], 2), "end": round(s["end"], 2),
                 "text": s["text"].strip()}
                for s in result.get("segments", [])
            ]
            log.info("[Long/S1] SUCCESS | chars=%d duration=%.1fs elapsed=%.2fs",
                     len(text), duration, time.time() - t0)
            return {
                "success": True, "text": text,
                "language": result.get("language", language),
                "duration_seconds": round(duration, 2),
                "segments": segments, "engine": "whisper-small",
                "chunk_count": 1, "failed_chunks": 0,
                "elapsed_sec": round(time.time() - t0, 2),
            }
        except ImportError:
            log.warning("[Long/S1] openai-whisper not installed — chunked fallback")
        except Exception as exc:
            log.error("[Long/S1] Whisper failed: %s", exc)

        # ── Stage 2: Chunked fallback ────────────────────────────────────────
        duration_total = _audio_duration_sec(wav_path)
        log.info("[Long/S2] Chunked fallback | total=%.1fs", duration_total)
        chunks_tmp, chunk_paths = _split_wav_chunks(wav_path)
        total = len(chunk_paths)
        texts, failed = [], 0
        try:
            for i, cp in enumerate(chunk_paths):
                log.info("[Long/S2] Chunk %d/%d …", i + 1, total)
                try:
                    sys.path.insert(0, _PROJECT_ROOT)
                    from speech_to_text import transcribe as _stt  # type: ignore
                    chunk_text = _stt(cp, language=language)
                    texts.append(chunk_text)
                    log.info("[Long/S2] Chunk %d/%d OK | chars=%d",
                             i + 1, total, len(chunk_text))
                except Exception as exc:
                    log.error("[Long/S2] Chunk %d/%d FAILED: %s", i + 1, total, exc)
                    failed += 1
        finally:
            import shutil as _sh; _sh.rmtree(chunks_tmp, ignore_errors=True)

        if texts:
            full_text = " ".join(t for t in texts if t.strip())
            log.info("[Long/S2] DONE | chunks=%d failed=%d chars=%d",
                     total, failed, len(full_text))
            return {
                "success": True, "text": full_text,
                "language": language,
                "duration_seconds": round(duration_total, 2),
                "segments": [], "engine": "project_stt_chunked",
                "chunk_count": total, "failed_chunks": failed,
                "elapsed_sec": round(time.time() - t0, 2),
            }
        return {
            "success": False,
            "error": "No STT engine available. Install: pip install openai-whisper",
            "chunk_count": total, "failed_chunks": failed,
        }
    finally:
        import shutil as _sh; _sh.rmtree(tmp_conv, ignore_errors=True)


def record_and_transcribe(duration_seconds: int = 5, language: str = "mr",
                           output_path: str = None) -> dict:
    """Record from microphone and transcribe."""
    log.info("=== record_and_transcribe START | duration=%ds language=%s ===",
             duration_seconds, language)

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

    log.info("Recording to %s for %ds", output_path, duration_seconds)
    try:
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore
        import numpy as np

        sample_rate = 16000
        log.info("Recording at %dHz for %ds", sample_rate, duration_seconds)
        recording = sd.rec(int(duration_seconds * sample_rate),
                           samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
        sf.write(output_path, recording, sample_rate)
        log.info("Recording saved: %s (%d bytes)", output_path, os.path.getsize(output_path))

    except ImportError:
        log.error("sounddevice/soundfile not installed. Run: pip install sounddevice soundfile")
        return {
            "success": False,
            "error": "Microphone recording requires: pip install sounddevice soundfile",
        }
    except Exception as exc:
        log.error("Recording failed: %s", exc)
        return {"success": False, "error": f"Recording failed: {exc}"}

    result = transcribe(output_path, language=language)
    result["audio_path"] = output_path
    return result


def main():
    parser = argparse.ArgumentParser(description="Marathi STT Bridge")
    sub = parser.add_subparsers(dest="cmd")

    t = sub.add_parser("transcribe")
    t.add_argument("--audio", required=True)
    t.add_argument("--language", default="mr")

    r = sub.add_parser("record")
    r.add_argument("--duration", type=int, default=5)
    r.add_argument("--language", default="mr")
    r.add_argument("--output", default=None)

    tl = sub.add_parser("transcribe-long")
    tl.add_argument("--audio", required=True)
    tl.add_argument("--language", default="mr")

    # Legacy: bare --audio shortcut
    parser.add_argument("--audio", help="(legacy) audio path")
    parser.add_argument("--language", default="mr")

    args = parser.parse_args()
    if args.cmd == "transcribe":
        print(json.dumps(transcribe(args.audio, args.language), ensure_ascii=False))
    elif args.cmd == "transcribe-long":
        print(json.dumps(transcribe_long_audio(args.audio, args.language),
                         ensure_ascii=False))
    elif args.cmd == "record":
        print(json.dumps(record_and_transcribe(args.duration, args.language,
                                               args.output), ensure_ascii=False))
    elif args.audio:
        print(json.dumps(transcribe(args.audio, args.language), ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
