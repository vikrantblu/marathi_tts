#!/usr/bin/env python3
"""Helper script: writes all bridge Python files."""
import os

DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marathi_tts_desktop", "python_bridge")

FILES = {}

# ─────────────────────────── ocr_bridge.py ───────────────────────────────
FILES["ocr_bridge.py"] = r'''#!/usr/bin/env python3
"""
OCR Bridge - Marathi Devanagari Image Text Extraction
======================================================
Usage:
    python ocr_bridge.py --image /path/to/image.png

Returns: JSON { success, text }
"""

import sys, os, json, argparse, traceback, time

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

log = get_logger("ocr_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("OCR Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)


def _preprocess_image(image):
    """Enhance image for Devanagari OCR. Falls back to original on error."""
    # Try web-app image processor first
    try:
        from tts.utils.text.image_processor import preprocess_image_for_ocr  # type: ignore
        result = preprocess_image_for_ocr(image)
        log.debug("Image preprocessed via web-app image_processor")
        return result
    except Exception as exc:
        log.debug("Web-app image_processor unavailable (%s) - using embedded", exc)

    # Embedded preprocessing using opencv + PIL
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageEnhance

        # Upscale small images
        if min(image.size) < 1000:
            scale = 1000 / min(image.size)
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.LANCZOS
            )
            log.debug("Image upscaled to %s", image.size)

        img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        _, thresh = cv2.threshold(denoised, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        from PIL import Image as PILImage
        pil = PILImage.fromarray(cleaned)
        enhanced = ImageEnhance.Contrast(pil).enhance(1.5)
        log.debug("Image preprocessed via embedded cv2 pipeline")
        return enhanced
    except ImportError as exc:
        log.warning("cv2/numpy not available (%s) - using raw PIL image", exc)
        return image
    except Exception as exc:
        log.error("Image preprocessing failed: %s", exc)
        return image


def extract_text(image_path: str) -> dict:
    """Extract Marathi text from image file.

    Returns: {success, text} or {success:False, error}
    """
    t0 = time.time()
    log.info("=== extract_text START | image=%s ===", image_path)

    if not os.path.exists(image_path):
        log.error("Image file not found: %s", image_path)
        return {"success": False, "error": f"File not found: {image_path}"}

    log.info("File size: %d bytes", os.path.getsize(image_path))

    # Stage 1: Full pipeline (web-app image_processor + pytesseract)
    log.info("[Stage 1] Full OCR pipeline")
    try:
        import pytesseract  # type: ignore
        from PIL import Image

        log.debug("Testing Tesseract availability")
        try:
            ver = pytesseract.get_tesseract_version()
            log.info("Tesseract version: %s", ver)
        except Exception as exc:
            log.error("Tesseract binary not found: %s", exc)
            return {
                "success": False,
                "error": "Tesseract OCR binary is not installed. "
                         "Download: https://github.com/UB-Mannheim/tesseract/wiki",
            }

        image = Image.open(image_path).convert("RGB")
        log.debug("Image opened: size=%s mode=%s", image.size, image.mode)

        processed = _preprocess_image(image)

        # Primary: OEM 1 (LSTM), PSM 6 (uniform block), Marathi+Hindi+Sanskrit
        config = r"--oem 1 --psm 6 -l mar+hin+san --dpi 300"
        log.info("[Stage 1] Running pytesseract | config=%s", config)
        t_ocr = time.time()
        text = pytesseract.image_to_string(processed, config=config)
        log.info("[Stage 1] OCR done in %.2fs | chars=%d", time.time() - t_ocr, len(text))

        # Fallback PSM if nothing extracted
        if not text or not text.strip():
            log.warning("[Stage 1] PSM 6 returned empty - trying PSM 3")
            text = pytesseract.image_to_string(processed,
                                               config=r"--oem 1 --psm 3 -l mar+hin --dpi 300")
            log.info("[Stage 1] PSM 3 result: chars=%d", len(text))

        text = text.strip()
        if not text:
            log.warning("[Stage 1] OCR returned empty text for this image")
            return {"success": False,
                    "error": "OCR could not extract any text from this image. "
                             "Ensure it contains clear Marathi/Devanagari text."}

        log.info("[Stage 1] SUCCESS | chars=%d elapsed=%.2fs",
                 len(text), time.time() - t0)
        return {"success": True, "text": text,
                "char_count": len(text), "elapsed_sec": round(time.time() - t0, 2)}

    except ImportError as exc:
        log.error("[Stage 1] Missing dependency: %s", exc)
        return {"success": False, "error": f"Missing package: {exc}. Run: pip install pytesseract pillow"}
    except Exception as exc:
        log.error("[Stage 1] OCR failed: %s\n%s", exc, traceback.format_exc())
        return {"success": False, "error": str(exc), "traceback": traceback.format_exc()}


def main():
    parser = argparse.ArgumentParser(description="Marathi OCR Bridge")
    parser.add_argument("--image", required=True, help="Path to image file")
    args = parser.parse_args()
    print(json.dumps(extract_text(args.image), ensure_ascii=False))


if __name__ == "__main__":
    main()
'''

# ─────────────────────────── pdf_bridge.py ───────────────────────────────
FILES["pdf_bridge.py"] = r'''#!/usr/bin/env python3
"""
PDF Bridge - Marathi PDF Text Extraction
==========================================
Extracts Marathi/Devanagari text from PDF files.

Usage:
    python pdf_bridge.py --pdf /path/to/document.pdf

Returns: JSON { success, text, method, page_count }

Extraction chain:
  1. PyMuPDF  (best for Devanagari font CIDFont/ToUnicode CMaps)
  2. PyPDF2   (lightweight fallback)
  3. OCR      (pdf2image + pytesseract, only if above two fail/score low)
"""

import sys, os, json, argparse, traceback, time, io

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

log = get_logger("pdf_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("PDF Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)


# ── Devanagari quality heuristic ──────────────────────────────────────────
_DEVANAGARI_RANGE = range(0x0900, 0x0980)

def _devanagari_ratio(text: str) -> float:
    if not text:
        return 0.0
    deva = sum(1 for c in text if ord(c) in _DEVANAGARI_RANGE)
    return deva / len(text)


def _reassemble(text: str) -> str:
    """Fix broken Devanagari from PDF extraction (spurious spaces inside syllables)."""
    try:
        from tts.utils.text.devanagari_reassembler import reassemble_devanagari  # type: ignore
        fixed = reassemble_devanagari(text)
        log.debug("Devanagari reassembler applied | before=%d after=%d chars",
                  len(text), len(fixed))
        return fixed
    except Exception:
        return text


def _extract_pymupdf(pdf_bytes: bytes) -> tuple:
    """Returns (text, page_count) or raises."""
    import fitz  # type: ignore
    log.debug("PyMuPDF: opening PDF (%d bytes)", len(pdf_bytes))
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        t = page.get_text("text") or ""
        if t.strip():
            pages.append(t)
            log.debug("PyMuPDF page %d: %d chars", i + 1, len(t))
    doc.close()
    return "\n\n".join(pages), len(doc)


def _extract_pypdf2(pdf_bytes: bytes) -> tuple:
    """Returns (text, page_count) or raises."""
    from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [p.extract_text() or "" for p in reader.pages]
    text = "\n\n".join(p for p in pages if p.strip())
    log.debug("PyPDF2: %d pages, %d chars extracted", len(reader.pages), len(text))
    return text, len(reader.pages)


def _extract_ocr(pdf_bytes: bytes) -> tuple:
    """Convert PDF pages to images, then OCR each. Returns (text, page_count)."""
    import pdf2image  # type: ignore
    import pytesseract  # type: ignore
    import tempfile
    from PIL import Image

    log.info("OCR extraction: converting PDF pages to images at 300dpi")
    with tempfile.TemporaryDirectory() as tmp:
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=300, output_folder=tmp)
        log.info("OCR extraction: %d page images generated", len(images))

        texts = []
        for i, img in enumerate(images):
            log.debug("OCR page %d/%d", i + 1, len(images))
            try:
                from tts.utils.text.image_processor import preprocess_image_for_ocr  # type: ignore
                img = preprocess_image_for_ocr(img)
            except Exception:
                pass
            t = pytesseract.image_to_string(img,
                                            config=r"--oem 1 --psm 6 -l mar+hin+san --dpi 300")
            if t.strip():
                texts.append(t.strip())
        return "\n\n".join(texts), len(images)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path: str) -> dict:
    """Extract Marathi text from PDF.

    Returns: {success, text, method, page_count} or {success:False, error}
    """
    t0 = time.time()
    log.info("=== extract_pdf START | file=%s ===", pdf_path)

    if not os.path.exists(pdf_path):
        log.error("PDF not found: %s", pdf_path)
        return {"success": False, "error": f"File not found: {pdf_path}"}

    log.info("PDF size: %d bytes", os.path.getsize(pdf_path))
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    candidates = []

    # Stage 1: PyMuPDF
    log.info("[Stage 1] PyMuPDF extraction")
    try:
        text, n_pages = _extract_pymupdf(pdf_bytes)
        score = _devanagari_ratio(text)
        log.info("[Stage 1] PyMuPDF: %d chars, %d pages, Devanagari ratio=%.3f",
                 len(text), n_pages, score)
        if text.strip():
            text = _reassemble(text)
            candidates.append({"text": text, "score": max(score, 0.1) * 0.8,
                                "method": "pymupdf", "page_count": n_pages})
    except ImportError:
        log.warning("[Stage 1] PyMuPDF (fitz) not installed")
    except Exception as exc:
        log.warning("[Stage 1] PyMuPDF failed: %s", exc)

    # Stage 2: PyPDF2
    log.info("[Stage 2] PyPDF2 extraction")
    try:
        text, n_pages = _extract_pypdf2(pdf_bytes)
        score = _devanagari_ratio(text)
        log.info("[Stage 2] PyPDF2: %d chars, %d pages, Devanagari ratio=%.3f",
                 len(text), n_pages, score)
        if text.strip():
            text = _reassemble(text)
            candidates.append({"text": text, "score": max(score, 0.05) * 0.5,
                                "method": "pypdf2", "page_count": n_pages})
    except ImportError:
        log.warning("[Stage 2] PyPDF2 not installed")
    except Exception as exc:
        log.warning("[Stage 2] PyPDF2 failed: %s", exc)

    # Stage 3: OCR (if no good candidates)
    best = max(candidates, key=lambda c: c["score"]) if candidates else None
    if not best or best["score"] < 0.3:
        log.info("[Stage 3] OCR fallback (best score so far: %s)",
                 best["score"] if best else "none")
        try:
            text, n_pages = _extract_ocr(pdf_bytes)
            score = _devanagari_ratio(text)
            log.info("[Stage 3] OCR: %d chars, %d pages, Devanagari ratio=%.3f",
                     len(text), n_pages, score)
            if text.strip():
                candidates.append({"text": text, "score": max(score, 0.1) * 0.7,
                                    "method": "ocr", "page_count": n_pages})
        except ImportError as exc:
            log.warning("[Stage 3] OCR dependencies missing: %s", exc)
        except Exception as exc:
            log.error("[Stage 3] OCR failed: %s\n%s", exc, traceback.format_exc())

    if not candidates:
        log.error("All extraction methods failed")
        return {"success": False, "error": "All extraction methods failed (PyMuPDF, PyPDF2, OCR)"}

    best = max(candidates, key=lambda c: c["score"])
    log.info("=== extract_pdf DONE | method=%s score=%.3f chars=%d elapsed=%.2fs ===",
             best["method"], best["score"], len(best["text"]), time.time() - t0)
    return {
        "success": True,
        "text": best["text"].strip(),
        "method": best["method"],
        "page_count": best.get("page_count", 0),
        "char_count": len(best["text"]),
        "elapsed_sec": round(time.time() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Marathi PDF Extraction Bridge")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    args = parser.parse_args()
    print(json.dumps(extract_pdf(args.pdf), ensure_ascii=False))


if __name__ == "__main__":
    main()
'''

# ─────────────────────────── correction_bridge.py ────────────────────────
FILES["correction_bridge.py"] = r'''#!/usr/bin/env python3
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
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
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


def _read_text_arg(args):
    """Resolve text from --text or --text-file."""
    text = getattr(args, "text", None)
    tf = getattr(args, "text_file", None)
    if tf:
        with open(tf, "r", encoding="utf-8") as fh:
            text = fh.read()
    return text


def main():
    parser = argparse.ArgumentParser(description="Marathi Text Correction Bridge")
    sub = parser.add_subparsers(dest="action")
    c = sub.add_parser("correct");  c.add_argument("--text", required=False, default=None)
    c.add_argument("--text-file", default=None)
    f = sub.add_parser("format");   f.add_argument("--text", required=False, default=None)
    f.add_argument("--text-file", default=None)
    s = sub.add_parser("suggest")
    s.add_argument("--incorrect", required=True)
    s.add_argument("--correct", required=True)
    s.add_argument("--category", default="general")
    parser.add_argument("--text", help="(legacy) text to correct")
    parser.add_argument("--text-file", default=None)

    args = parser.parse_args()
    text = _read_text_arg(args)
    if args.action == "correct" or (args.action is None and text):
        if not text:
            print(json.dumps({"success": False, "error": "No --text or --text-file provided"}))
            sys.exit(1)
        print(json.dumps(correct_text(text), ensure_ascii=False))
    elif args.action == "format":
        if not text:
            print(json.dumps({"success": False, "error": "No --text or --text-file provided"}))
            sys.exit(1)
        print(json.dumps(format_text(text), ensure_ascii=False))
    elif args.action == "suggest":
        print(json.dumps(suggest_correction(args.incorrect, args.correct,
                                            args.category), ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
'''

# ─────────────────────────── stt_bridge.py ───────────────────────────────
FILES["stt_bridge.py"] = r'''#!/usr/bin/env python3
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

    # Legacy: bare --audio shortcut
    parser.add_argument("--audio", help="(legacy) audio path")
    parser.add_argument("--language", default="mr")

    args = parser.parse_args()
    if args.cmd == "transcribe":
        print(json.dumps(transcribe(args.audio, args.language), ensure_ascii=False))
    elif args.cmd == "record":
        print(json.dumps(record_and_transcribe(args.duration, args.language,
                                               args.output), ensure_ascii=False))
    elif args.audio:
        print(json.dumps(transcribe(args.audio, args.language), ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
'''

# ─────────────────────────── web_bridge.py ───────────────────────────────
FILES["web_bridge.py"] = r'''#!/usr/bin/env python3
"""
Web Bridge - Marathi Website Content Fetcher
============================================
Fetches and extracts Marathi text content from a URL.

Usage:
    python web_bridge.py --url https://example.com

Returns: JSON { success, text, title, image_texts_count }
"""

import sys, os, json, argparse, traceback, time, re

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

log = get_logger("web_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("Web Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "mr,hi;q=0.9,en;q=0.8",
}


def _clean_text(raw: str) -> str:
    """Clean extracted web text. Falls back to simple regex if web util unavailable."""
    try:
        from tts.utils.text.text_processor import clean_web_text  # type: ignore
        result = clean_web_text(raw)
        log.debug("clean_web_text applied via web-app | %d -> %d chars", len(raw), len(result))
        return result
    except Exception:
        pass
    # Embedded fallback
    text = re.sub(r"[ \t]{2,}", " ", raw)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ocr_image_url(img_url: str, base_url: str) -> str:
    """Download image from URL and OCR it. Returns text or empty string."""
    try:
        import requests  # type: ignore
        from PIL import Image  # type: ignore
        import io as _io
        import pytesseract  # type: ignore

        if not img_url.startswith("http"):
            base = "/".join(base_url.split("/")[:3])
            img_url = base + ("" if img_url.startswith("/") else "/") + img_url

        resp = requests.get(img_url, timeout=8, headers=_HEADERS)
        img = Image.open(_io.BytesIO(resp.content))
        text = pytesseract.image_to_string(img, lang="mar+hin")
        log.debug("Image OCR from %s | chars=%d", img_url[:60], len(text))
        return text.strip()
    except Exception as exc:
        log.debug("Image OCR skipped for %s: %s", img_url[:60], exc)
        return ""


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def fetch_url(url: str, process_images: bool = True) -> dict:
    """Fetch and extract Marathi text from a URL.

    Returns: {success, text, title, image_texts_count}
    """
    t0 = time.time()
    log.info("=== fetch_url START | url=%s process_images=%s ===", url, process_images)

    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:
        log.error("Missing dependency: %s. Run: pip install requests beautifulsoup4", exc)
        return {"success": False, "error": f"Missing package: {exc}"}

    try:
        log.info("HTTP GET %s", url)
        t_req = time.time()
        resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        log.info("HTTP %d | %.2fs | content_len=%d",
                 resp.status_code, time.time() - t_req, len(resp.content))

        # Detect encoding from Content-Type header only (avoid slow chardet scan)
        content_type = resp.headers.get("content-type", "")
        ct_charset = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                ct_charset = part.split("=", 1)[1].strip()
                break
        encoding = ct_charset if ct_charset else "utf-8"
        # iso-8859-1 is a browser default placeholder; real Marathi pages are utf-8
        if encoding.lower() == "iso-8859-1":
            encoding = "utf-8"
        html = resp.content.decode(encoding, errors="replace")
        log.info("Decoded with encoding=%s", encoding)

        # Use lxml for faster parsing; fall back to html.parser if unavailable
        try:
            soup = BeautifulSoup(html, "lxml")
            log.debug("HTML parsed with lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
            log.debug("HTML parsed with html.parser (lxml unavailable)")

        # Remove noise tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form",
                         "noscript", "iframe"]):
            tag.decompose()

        # Title
        title_tag = soup.find("title") or soup.find("h1") or soup.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else ""
        log.info("Page title: %s", title[:100])

        # Main content
        content_tag = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=lambda c: c and "content" in c.lower()) or
            soup.find("body")
        )
        raw_text = content_tag.get_text(separator="\n", strip=True) if content_tag else ""
        log.info("Raw text extracted: %d chars", len(raw_text))

        cleaned_text = _clean_text(raw_text)
        log.info("Cleaned text: %d chars", len(cleaned_text))

        # Add title prefix
        if title:
            cleaned_text = f"{title}\n\n{cleaned_text}"

        # Image OCR (optional) — capped at 30 s total
        image_texts = []
        if process_images:
            img_tags = soup.find_all("img", src=True)[:5]
            log.info("Processing %d images for OCR (budget=30s)", len(img_tags))
            ocr_budget = 30.0
            for img_tag in img_tags:
                if ocr_budget <= 0:
                    log.info("OCR time budget exhausted, skipping remaining images")
                    break
                t_img = time.time()
                ocr_text = _ocr_image_url(img_tag["src"], url)
                ocr_budget -= time.time() - t_img
                if ocr_text and len(ocr_text) > 20:
                    image_texts.append(ocr_text)

        if image_texts:
            cleaned_text += "\n\n[Image Text]\n" + "\n".join(image_texts)

        log.info("=== fetch_url DONE | chars=%d img_texts=%d elapsed=%.2fs ===",
                 len(cleaned_text), len(image_texts), time.time() - t0)
        return {
            "success": True, "text": cleaned_text, "title": title,
            "image_texts_count": len(image_texts),
            "char_count": len(cleaned_text),
            "elapsed_sec": round(time.time() - t0, 2),
        }

    except Exception as exc:
        log.error("fetch_url failed: %s\n%s", exc, traceback.format_exc())
        return {"success": False, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="Web Content Fetch Bridge")
    parser.add_argument("--url", required=True)
    parser.add_argument("--no-images", action="store_true",
                        help="Skip image OCR")
    args = parser.parse_args()
    print(json.dumps(fetch_url(args.url, not args.no_images), ensure_ascii=False))


if __name__ == "__main__":
    main()
'''

# ───────────────────── script_converter_bridge.py ────────────────────────
FILES["script_converter_bridge.py"] = r'''#!/usr/bin/env python3
"""
Script Converter Bridge - Ancient Script to Devanagari
=======================================================
Converts Modi, Brahmi, and IAST scripts to/from Devanagari.

Usage:
    python script_converter_bridge.py --text "..." --mode modi_to_devanagari
    python script_converter_bridge.py --text "..." --mode devanagari_to_iast
    python script_converter_bridge.py --text "..." --mode iast_to_devanagari
    python script_converter_bridge.py --text "..." --mode brahmi_to_devanagari

Returns: JSON { success, converted_text, mode, char_count }
"""

import sys, os, json, argparse, traceback, time

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

log = get_logger("script_converter_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _BRIDGE_DIR
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("Script Converter Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)

MODES = ["modi_to_devanagari", "devanagari_to_iast", "iast_to_devanagari", "brahmi_to_devanagari"]

# Embedded minimal Modi->Devanagari mapping (core characters)
_EMBEDDED_MODI_MAP = {
    "\U00011600": "\u0915",  # MODI LETTER KA -> क
    "\U00011601": "\u0916",  # KHA -> ख
    "\U00011602": "\u0917",  # GA  -> ग
    "\U00011603": "\u0918",  # GHA -> घ
    "\U00011604": "\u0919",  # NGA -> ङ
    "\U00011605": "\u091A",  # CA  -> च
    "\U00011606": "\u091B",  # CHA -> छ
    "\U00011607": "\u091C",  # JA  -> ज
    "\U00011608": "\u091D",  # JHA -> झ
    "\U00011609": "\u091E",  # NYA -> ञ
    "\U0001160A": "\u091F",  # TTA -> ट
    "\U0001160B": "\u0920",  # TTHA-> ठ
    "\U0001160C": "\u0921",  # DDA -> ड
    "\U0001160D": "\u0922",  # DDHA-> ढ
    "\U0001160E": "\u0923",  # NNA -> ण
    "\U0001160F": "\u0924",  # TA  -> त
    "\U00011610": "\u0925",  # THA -> थ
    "\U00011611": "\u0926",  # DA  -> द
    "\U00011612": "\u0927",  # DHA -> ध
    "\U00011613": "\u0928",  # NA  -> न
    "\U00011614": "\u092A",  # PA  -> प
    "\U00011615": "\u092B",  # PHA -> फ
    "\U00011616": "\u092C",  # BA  -> ब
    "\U00011617": "\u092D",  # BHA -> भ
    "\U00011618": "\u092E",  # MA  -> म
    "\U00011619": "\u092F",  # YA  -> य
    "\U0001161A": "\u0930",  # RA  -> र
    "\U0001161B": "\u0932",  # LA  -> ल
    "\U0001161C": "\u0935",  # VA  -> व
    "\U0001161D": "\u0936",  # SHA -> श
    "\U0001161E": "\u0937",  # SSA -> ष
    "\U0001161F": "\u0938",  # SA  -> स
    "\U00011620": "\u0939",  # HA  -> ह
}


def _indic_transliterate(text: str, src_scheme, dst_scheme) -> str:
    """Transliterate using indic-transliteration library."""
    from indic_transliteration import sanscript  # type: ignore
    from indic_transliteration.sanscript import transliterate  # type: ignore
    return transliterate(text, src_scheme, dst_scheme)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def convert(text: str, mode: str = "modi_to_devanagari") -> dict:
    """Convert script text between supported modes.

    Returns: {success, converted_text, mode, char_count, original_char_count}
    """
    t0 = time.time()
    log.info("=== convert START | mode=%s text_len=%d ===", mode, len(text))
    log.debug("Input text preview: %.100s", text)

    if not text.strip():
        return {"success": False, "error": "Empty input text"}
    if mode not in MODES:
        return {"success": False, "error": f"Unsupported mode '{mode}'. Choose: {MODES}"}

    result = None

    # ── Modi -> Devanagari ─────────────────────────────────────────────────
    if mode == "modi_to_devanagari":
        # Try web-app ScriptConverter first
        try:
            from tts.utils.text.script_converter import ScriptConverter  # type: ignore
            result = ScriptConverter.modi_to_devanagari(text)
            log.info("modi_to_devanagari via ScriptConverter | %d -> %d chars",
                     len(text), len(result))
        except Exception as exc:
            log.warning("ScriptConverter unavailable (%s) - using embedded map", exc)

        # Embedded fallback
        if result is None:
            try:
                # Try constants map first
                from tts.constants.script_constants import MODI_TO_DEVANAGARI_MAP  # type: ignore
                result = "".join(MODI_TO_DEVANAGARI_MAP.get(c, c) for c in text)
                log.info("modi_to_devanagari via constants map")
            except Exception:
                result = "".join(_EMBEDDED_MODI_MAP.get(c, c) for c in text)
                log.info("modi_to_devanagari via embedded map")

    # ── Devanagari -> IAST ─────────────────────────────────────────────────
    elif mode == "devanagari_to_iast":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
            log.info("devanagari_to_iast via indic-transliteration | %d -> %d chars",
                     len(text), len(result))
        except ImportError:
            log.error("indic-transliteration not installed. Run: pip install indic-transliteration")
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            log.error("devanagari_to_iast failed: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── IAST -> Devanagari ─────────────────────────────────────────────────
    elif mode == "iast_to_devanagari":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
            log.info("iast_to_devanagari via indic-transliteration | %d -> %d chars",
                     len(text), len(result))
        except ImportError:
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── Brahmi -> Devanagari ───────────────────────────────────────────────
    elif mode == "brahmi_to_devanagari":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.BRAHMI, sanscript.DEVANAGARI)
            log.info("brahmi_to_devanagari | %d -> %d chars", len(text), len(result))
        except ImportError:
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if result is None:
        return {"success": False, "error": "Conversion produced no result"}

    log.info("=== convert DONE | mode=%s %d -> %d chars elapsed=%.2fs ===",
             mode, len(text), len(result), time.time() - t0)
    return {
        "success": True,
        "converted_text": result,
        "mode": mode,
        "char_count": len(result),
        "original_char_count": len(text),
        "elapsed_sec": round(time.time() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Marathi Script Converter Bridge")
    parser.add_argument("--text", required=False, default=None)
    parser.add_argument("--text-file", default=None,
                        help="Read --text from a UTF-8 file (avoids CLI escaping issues)")
    parser.add_argument("--mode", default="modi_to_devanagari", choices=MODES)
    args = parser.parse_args()
    text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not text:
        print(json.dumps({"success": False, "error": "No --text or --text-file provided"}))
        sys.exit(1)
    print(json.dumps(convert(text, args.mode), ensure_ascii=False))


if __name__ == "__main__":
    main()
'''

# ─────────────────────────── Write all files ─────────────────────────────
for filename, content in FILES.items():
    path = os.path.join(DEST, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written: {path}")

print("All bridge scripts written successfully.")
