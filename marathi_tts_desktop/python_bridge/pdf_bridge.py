#!/usr/bin/env python3
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
    n_pages = len(doc)  # capture BEFORE close
    pages = []
    for i, page in enumerate(doc):
        t = page.get_text("text") or ""
        if t.strip():
            pages.append(t)
            log.debug("PyMuPDF page %d: %d chars", i + 1, len(t))
    doc.close()
    return "\n\n".join(pages), n_pages


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
