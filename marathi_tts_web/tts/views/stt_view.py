import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Add project speech_to_text module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@csrf_protect
@require_http_methods(["POST"])
def transcribe_audio(request):
    """
    Transcribe uploaded audio file to Marathi (or chosen language) text.
    Uses OpenAI Whisper if available, otherwise falls back to DeepSpeech / fallback stub.
    """
    try:
        audio_file = request.FILES.get("audio")
        language = request.POST.get("language", "mr")

        if not audio_file:
            return JsonResponse({"success": False, "error": "Audio file is required"}, status=400)

        # Validate audio upload: size limit (100 MB)
        from ..utils.security import validate_audio_upload
        is_valid, err_msg = validate_audio_upload(audio_file)
        if not is_valid:
            return JsonResponse({"success": False, "error": err_msg}, status=400)

        # Save uploaded file to a temp location
        suffix = os.path.splitext(audio_file.name)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            transcript, segments, engine = _do_transcribe(tmp_path, language)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return JsonResponse({
            "success": True,
            "transcript": transcript,
            "segments": segments,
            "engine": engine,
            "language": language,
        })

    except Exception as exc:
        logger.exception("STT transcription failed: %s", exc)
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


def _do_transcribe(audio_path: str, language: str):
    """Try Whisper → project speech_to_text → stub fallback."""
    # ── Tier 1: OpenAI Whisper ───────────────────────────────────────────────
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language or None, task="transcribe")
        segments = [
            {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in result.get("segments", [])
        ]
        return result["text"].strip(), segments, "whisper"
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Whisper failed: %s", exc)

    # ── Tier 2: project speech_to_text module ────────────────────────────────
    try:
        from speech_to_text import transcribe as project_transcribe
        text = project_transcribe(audio_path, language=language)
        return text, [], "project_stt"
    except Exception as exc:
        logger.warning("Project STT failed: %s", exc)

    # ── Tier 3: stub (for dev/demo) ──────────────────────────────────────────
    return "(Transcription unavailable — install openai-whisper)", [], "unavailable"
