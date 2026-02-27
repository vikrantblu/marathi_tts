#!/usr/bin/env python3
"""
Emotion Bridge - Marathi Text Emotion Analysis
================================================
Detects emotion in Marathi text and returns voice modulation parameters.

Usage:
    python emotion_bridge.py --text "मराठी मजकूर"

Returns: JSON { success, emotion, scores, voice_params, intensity }
"""

import sys, os, json, argparse, re, traceback, time

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

log = get_logger("emotion_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("Emotion Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)

# ---------------------------------------------------------------------------
# Embedded emotion keywords (copied from tts/constants/emotion_constants.py)
# ---------------------------------------------------------------------------

_EMOTION_KEYWORDS = {
    "happy":   ["आनंद","खुशी","हर्ष","आनंदी","मजा","उल्हास","उत्साह","हसणे",
                 "खुश","हास्य","मनोरंजन","प्रसन्न","अभिनंदन","सुख","समाधान",
                 "उत्साही","मस्त","प्रेम","स्नेह"],
    "sad":     ["दुःख","शोक","रडणे","कष्ट","वेदना","पीडा","दुःखी","उदास",
                 "निराश","एकटा","अश्रू","रडू","दुखापत","विरहाचे","कष्टी",
                 "वाईट","हताश","विषादी"],
    "angry":   ["राग","क्रोध","संताप","चिडचिड","रागीट","रागावणे","भडकणे",
                 "रोष","द्वेष","कोप","आक्रमक","उग्र","तावातावाने","संतापी","क्रोधित"],
    "fear":    ["भय","भीती","धास्ती","घाबरणे","दहशत","त्रास","धोका",
                 "असुरक्षित","धाक","काळजी","भयभीत","घाबरलेला","भयानक","धोकादायक"],
    "surprise":["आश्चर्य","अचंबित","चकित","अनपेक्षित","थक्क","आश्चर्यचकित",
                 "विस्मय","धक्कादायक","अचानक","अविश्वसनीय","नवलपूर्ण"],
    "disgust": ["घृणा","तिरस्कार","नापसंती","नाराजी","अढी","कटुता",
                 "अप्रिय","शिसारणे"],
    "love":    ["प्रेम","माया","आपुलकी","जिव्हाळा","ममता","स्नेह","मायेने",
                 "प्रीती","वात्सल्य","प्रेमळ","मायाळू","आत्मीयता","प्रणय"],
    "devotional":["भक्ती","प्रार्थना","विनंती","स्तुती","आराधना","पूजा",
                   "नमन","वंदन","जप","ध्यान","समर्पण","देव","परमेश्वर"],
    "peaceful": ["शांत","समाधान","स्थिर","निवांत","शांतता","विश्रांती","निर्मळ","मोकळे"],
    "neutral":  [],
}

_VOICE_PARAMS = {
    "happy":     {"pitch": 1.15, "speed": 1.10, "volume": 2.0},
    "sad":       {"pitch": 0.90, "speed": 0.90, "volume": -1.5},
    "angry":     {"pitch": 1.10, "speed": 1.15, "volume": 3.0},
    "fear":      {"pitch": 1.05, "speed": 1.10, "volume": 1.5},
    "surprise":  {"pitch": 1.20, "speed": 1.05, "volume": 2.5},
    "disgust":   {"pitch": 0.95, "speed": 0.95, "volume": 0.0},
    "love":      {"pitch": 1.05, "speed": 0.95, "volume": 1.0},
    "devotional":{"pitch": 0.95, "speed": 0.90, "volume": 0.5},
    "peaceful":  {"pitch": 0.95, "speed": 0.85, "volume": -0.5},
    "neutral":   {"pitch": 1.00, "speed": 1.00, "volume": 0.0},
}


def _keyword_analysis(text: str) -> dict:
    """Standalone keyword-based emotion analysis."""
    word_count = max(len(re.findall(r"\S+", text)), 1)
    scores = {e: 0.0 for e in _EMOTION_KEYWORDS}

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        for kw in keywords:
            count = len(re.findall(re.escape(kw), text))
            scores[emotion] += count / word_count

    non_neutral = {e: v for e, v in scores.items() if e != "neutral" and v > 0}
    dominant = max(non_neutral, key=non_neutral.get) if non_neutral else "neutral"
    if dominant == "neutral":
        scores["neutral"] = 1.0

    total = sum(scores.values()) or 1.0
    norm_scores = {e: round(v / total, 4) for e, v in scores.items()}

    intensity = min(1.0, sum(v for e, v in non_neutral.items()) * 5) if non_neutral else 0.0
    log.debug("Keyword analysis: dominant=%s intensity=%.3f scores=%s",
              dominant, intensity, {k: v for k, v in norm_scores.items() if v > 0})
    return {
        "emotion": dominant,
        "dominant": dominant,
        "intensity": round(intensity, 3),
        "scores": norm_scores,
        "voice_params": _VOICE_PARAMS.get(dominant, _VOICE_PARAMS["neutral"]),
    }


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def analyze_emotion(text: str) -> dict:
    """Analyze emotion in Marathi text.

    Returns: {success, emotion, dominant, intensity, scores, voice_params}
    """
    t0 = time.time()
    log.info("=== analyze_emotion START | text_len=%d ===", len(text))

    if not text or not text.strip():
        log.error("Empty input text")
        return {"success": False, "error": "Empty text"}

    # Stage 1: Full EmotionAnalyzer (from copied tts package)
    log.info("[Stage 1] Attempting full EmotionAnalyzer")
    try:
        from tts.utils.emotion.emotion_analyzer import EmotionAnalyzer  # type: ignore
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze(text)
        log.info("[Stage 1] EmotionAnalyzer SUCCESS | dominant=%s intensity=%s",
                 result.get("dominant"), result.get("intensity"))
        result["success"] = True
        result["elapsed_sec"] = round(time.time() - t0, 3)
        return result
    except ImportError:
        log.info("[Stage 1] EmotionAnalyzer not available")
    except Exception as exc:
        log.warning("[Stage 1] EmotionAnalyzer failed: %s", exc)
        log.debug(traceback.format_exc())

    # Stage 2: Embedded keyword analysis
    log.info("[Stage 2] Using embedded keyword analysis")
    try:
        result = _keyword_analysis(text)
        result["success"] = True
        result["method"] = "keyword_analysis"
        result["elapsed_sec"] = round(time.time() - t0, 3)
        log.info("[Stage 2] SUCCESS | dominant=%s intensity=%.3f",
                 result["dominant"], result["intensity"])
        return result
    except Exception as exc:
        log.error("[Stage 2] Keyword analysis failed: %s\n%s", exc, traceback.format_exc())
        return {"success": False, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="Marathi Emotion Analyser Bridge")
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    print(json.dumps(analyze_emotion(args.text), ensure_ascii=False))


if __name__ == "__main__":
    main()
