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
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
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
        if os.path.isdir(_PROJECT_ROOT) and _PROJECT_ROOT not in sys.path:
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
