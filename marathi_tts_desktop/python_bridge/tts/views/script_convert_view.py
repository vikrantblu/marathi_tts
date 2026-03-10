import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Modi → Devanagari character map (basic subset — full table in indic-transliteration)
_MODI_TO_DEVA = {
    "𑙀": "ा", "𑘩": "ल", "𑘩्": "ल्", "𑘇": "इ", "𑘈": "ई",
    "𑘃": "अ", "𑘄": "आ", "𑘅": "इ", "𑘆": "ई", "𑘉": "उ",
    "𑘊": "ऊ", "𑘋": "ऋ", "𑘌": "ए", "𑘍": "ऐ", "𑘎": "ओ",
    "𑘏": "औ", "𑘐": "क", "𑘑": "ख", "𑘒": "ग", "𑘓": "घ",
    "𑘔": "ङ", "𑘕": "च", "𑘖": "छ", "𑘗": "ज", "𑘘": "झ",
    "𑘙": "ञ", "𑘚": "ट", "𑘛": "ठ", "𑘜": "ड", "𑘝": "ढ",
    "𑘞": "ण", "𑘟": "त", "𑘠": "थ", "𑘡": "द", "𑘢": "ध",
    "𑘣": "न", "𑘤": "प", "𑘥": "फ", "𑘦": "ब", "𑘧": "भ",
    "𑘨": "म", "𑘩": "य", "𑘪": "र", "𑘫": "ल", "𑘬": "व",
    "𑘭": "श", "𑘮": "ष", "𑘯": "स", "𑘰": "ह",
}


@csrf_protect
@require_http_methods(["POST"])
def convert_script(request):
    """
    Convert text between Marathi scripts.
    POST body: { "text": "...", "mode": "modi_to_devanagari|devanagari_to_iast|iast_to_devanagari|brahmi_to_devanagari" }
    """
    try:
        body = json.loads(request.body)
        text = body.get("text", "").strip()
        mode = body.get("mode", "modi_to_devanagari")

        if not text:
            return JsonResponse({"success": False, "error": "Text is required"}, status=400)

        converted = _convert(text, mode)
        return JsonResponse({
            "success": True,
            "converted": converted,
            "mode": mode,
            "input_length": len(text),
            "output_length": len(converted),
        })

    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"success": False, "error": f"Invalid request: {exc}"}, status=400)
    except Exception as exc:
        logger.exception("Script conversion failed: %s", exc)
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


def _convert(text: str, mode: str) -> str:
    """Dispatch to the appropriate converter."""
    # ── Try indic-transliteration first ─────────────────────────────────────
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate

        scheme_map = {
            "devanagari_to_iast": (sanscript.DEVANAGARI, sanscript.IAST),
            "iast_to_devanagari": (sanscript.IAST, sanscript.DEVANAGARI),
            "brahmi_to_devanagari": (sanscript.BRAHMI, sanscript.DEVANAGARI),
        }
        if mode in scheme_map:
            src, tgt = scheme_map[mode]
            return transliterate(text, src, tgt)

        if mode == "modi_to_devanagari":
            return _modi_fallback(text)

    except ImportError:
        logger.warning("indic-transliteration not installed; using fallback")
    except Exception as exc:
        logger.warning("indic-transliteration error: %s; using fallback", exc)

    # ── Pure-Python fallbacks ────────────────────────────────────────────────
    if mode == "modi_to_devanagari":
        return _modi_fallback(text)
    if mode == "devanagari_to_iast":
        return _deva_to_iast_fallback(text)
    if mode == "iast_to_devanagari":
        return _iast_to_deva_fallback(text)
    return text  # brahmi without library — return as-is


def _modi_fallback(text: str) -> str:
    result = []
    for ch in text:
        result.append(_MODI_TO_DEVA.get(ch, ch))
    return "".join(result)


_DEVA_TO_IAST = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū",
    "ऋ": "ṛ", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "क": "ka", "ख": "kha", "ग": "ga", "घ": "gha", "ङ": "ṅa",
    "च": "ca", "छ": "cha", "ज": "ja", "झ": "jha", "ञ": "ña",
    "ट": "ṭa", "ठ": "ṭha", "ड": "ḍa", "ढ": "ḍha", "ण": "ṇa",
    "त": "ta", "थ": "tha", "द": "da", "ध": "dha", "न": "na",
    "प": "pa", "फ": "pha", "ब": "ba", "भ": "bha", "म": "ma",
    "य": "ya", "र": "ra", "ल": "la", "व": "va",
    "श": "śa", "ष": "ṣa", "स": "sa", "ह": "ha",
    "ं": "ṃ", "ः": "ḥ", "्": "", "ा": "ā", "ि": "i", "ी": "ī",
    "ु": "u", "ू": "ū", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
}

_IAST_TO_DEVA = {v: k for k, v in _DEVA_TO_IAST.items() if v}


def _deva_to_iast_fallback(text: str) -> str:
    result = []
    for ch in text:
        result.append(_DEVA_TO_IAST.get(ch, ch))
    return "".join(result)


def _iast_to_deva_fallback(text: str) -> str:
    out = text
    for iast, deva in sorted(_IAST_TO_DEVA.items(), key=lambda x: -len(x[0])):
        out = out.replace(iast, deva)
    return out
