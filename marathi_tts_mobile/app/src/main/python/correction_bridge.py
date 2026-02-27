#!/usr/bin/env python3
"""
Correction Bridge - Marathi Text Correction
=============================================
Corrects and formats Marathi text using AI model, grammar engine, or regex.

Usage:
    python correction_bridge.py correct --text "चुकीचा मजकूर"
    python correction_bridge.py format  --text "मजकूर"
    python correction_bridge.py suggest --incorrect "चुकीचा" --correct "बरोबर"

Returns: JSON { success, corrected_text, method }
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

log = get_logger("correction_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("Correction Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)


def _regex_clean(text: str) -> str:
    """Embedded regex-based basic Marathi text cleanup."""
    cleaned = text

    # Remove URLs and emails
    cleaned = re.sub(r"https?://\S+|www\.\S+|\S+@\S+\.\S+", "", cleaned)

    # Fix punctuation spacing
    cleaned = re.sub(r"\s+([।,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"([।])\s*\n", r"\1\n\n", cleaned)

    # Collapse runs of blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Remove blog/nav noise
    cleaned = re.sub(
        r"(Share|Subscribe|Comments?|Tags?|Categories?|Posted by|Filed under|Read more)[^\n]*",
        "", cleaned, flags=re.IGNORECASE,
    )

    # Strip lines that are pure noise (numbers, single chars, etc.)
    lines = [l.strip() for l in cleaned.splitlines()]
    lines = [l for l in lines if len(l) > 1 or "\u0900" <= (l[0:1] or "\x00") <= "\u097F"]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def correct_text(text: str) -> dict:
    """Apply spelling/grammar correction to Marathi text."""
    t0 = time.time()
    log.info("=== correct_text START | text_len=%d ===", len(text))

    if not text or not text.strip():
        return {"success": False, "error": "Empty text"}

    # Stage 1: AI correction model
    log.info("[Stage 1] AI correction model")
    try:
        from pathlib import Path
        from models.correction_model import MarathiCorrectionModel  # type: ignore
        model_path = Path(_PROJECT_ROOT) / "models" / "marathi-correction-model"
        if model_path.exists():
            model = MarathiCorrectionModel(model_path=str(model_path))
            corrected = model.correct_text_marathi(text)
            log.info("[Stage 1] AI model SUCCESS | %d -> %d chars, elapsed=%.2fs",
                     len(text), len(corrected), time.time() - t0)
            return {"success": True, "corrected_text": corrected,
                    "original_text": text, "method": "ai_model",
                    "elapsed_sec": round(time.time() - t0, 2)}
        else:
            log.info("[Stage 1] AI model path not found: %s", model_path)
    except ImportError:
        log.info("[Stage 1] AI correction model not available")
    except Exception as exc:
        log.warning("[Stage 1] AI model failed: %s", exc)
        log.debug(traceback.format_exc())

    # Stage 2: Grammar engine
    log.info("[Stage 2] MarathiGrammarEngine")
    try:
        from tts.utils.text.marathi_grammar import MarathiGrammarEngine  # type: ignore
        engine = MarathiGrammarEngine()
        corrected = engine.process(text)
        log.info("[Stage 2] Grammar engine SUCCESS | %d -> %d chars, elapsed=%.2fs",
                 len(text), len(corrected), time.time() - t0)
        return {"success": True, "corrected_text": corrected,
                "original_text": text, "method": "grammar_engine",
                "elapsed_sec": round(time.time() - t0, 2)}
    except ImportError:
        log.info("[Stage 2] Grammar engine not available")
    except Exception as exc:
        log.warning("[Stage 2] Grammar engine failed: %s", exc)

    # Stage 3: Regex cleanup only
    log.info("[Stage 3] Regex-based cleanup")
    try:
        corrected = _regex_clean(text)
        log.info("[Stage 3] Regex cleanup applied | %d -> %d chars, elapsed=%.2fs",
                 len(text), len(corrected), time.time() - t0)
        return {"success": True, "corrected_text": corrected,
                "original_text": text, "method": "regex_cleanup",
                "elapsed_sec": round(time.time() - t0, 2)}
    except Exception as exc:
        log.error("[Stage 3] Regex cleanup failed: %s", exc)
        return {"success": False, "error": str(exc)}


def format_text(text: str) -> dict:
    """Clean and reformat Marathi text."""
    t0 = time.time()
    log.info("=== format_text START | text_len=%d ===", len(text))
    try:
        cleaned = _regex_clean(text)
        log.info("format_text done | %d -> %d chars, elapsed=%.2fs",
                 len(text), len(cleaned), time.time() - t0)
        return {"success": True, "formatted_text": cleaned,
                "original_text": text, "elapsed_sec": round(time.time() - t0, 2)}
    except Exception as exc:
        log.error("format_text failed: %s", exc)
        return {"success": False, "error": str(exc)}


def suggest_correction(incorrect: str, correct: str, category: str = "general") -> dict:
    """Save a correction suggestion for future model training."""
    import csv, pathlib
    csv_path = pathlib.Path(_PROJECT_ROOT) / "correction_rules.csv"
    log.info("suggest_correction | incorrect=%r correct=%r category=%s",
             incorrect, correct, category)
    try:
        exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["incorrect_text", "correct_text", "category", "validation_status"])
            w.writerow([incorrect.strip(), correct.strip(), category, "pending"])
        log.info("Correction saved to %s", csv_path)
        return {"success": True, "message": f"Saved to {csv_path.name}",
                "incorrect": incorrect, "correct": correct}
    except Exception as exc:
        log.error("Failed to save correction: %s", exc)
        return {"success": False, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="Marathi Text Correction Bridge")
    sub = parser.add_subparsers(dest="action")
    c = sub.add_parser("correct");  c.add_argument("--text", required=True)
    f = sub.add_parser("format");   f.add_argument("--text", required=True)
    s = sub.add_parser("suggest")
    s.add_argument("--incorrect", required=True)
    s.add_argument("--correct", required=True)
    s.add_argument("--category", default="general")
    parser.add_argument("--text", help="(legacy) text to correct")

    args = parser.parse_args()
    if args.action == "correct" or (args.action is None and args.text):
        print(json.dumps(correct_text(args.text), ensure_ascii=False))
    elif args.action == "format":
        print(json.dumps(format_text(args.text), ensure_ascii=False))
    elif args.action == "suggest":
        print(json.dumps(suggest_correction(args.incorrect, args.correct,
                                            args.category), ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
