import PyPDF2
import io
import os
import logging
import tempfile
from django.http import JsonResponse

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import fitz  # PyMuPDF — much better Devanagari handling
except ImportError:
    fitz = None

from ..utils.text.image_processor import preprocess_image_for_ocr
from ..utils.text.devanagari_reassembler import (
    reassemble_devanagari, is_broken_devanagari, quality_score
)

logger = logging.getLogger('tts.pdf')


def extract_pdf_text(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']

        # Validate PDF upload: header check + size limit (50 MB)
        from ..utils.security import validate_pdf_upload
        is_valid, err_msg = validate_pdf_upload(pdf_file)
        if not is_valid:
            return JsonResponse({'success': False, 'error': err_msg}, status=400)

        try:
            pdf_bytes = pdf_file.read()
            candidates = []  # list of (text, score, method_name)

            # ── Method 1: PyMuPDF (best for Devanagari fonts) ─────────
            if fitz is not None:
                raw = _extract_with_pymupdf(pdf_bytes)
                if raw and raw.strip():
                    text, score, was_broken = _process_candidate(raw)
                    candidates.append((text, score, 'pymupdf', was_broken))
                    logger.info(f"PyMuPDF: score={score}, broken={was_broken}")

            # ── Method 2: PyPDF2 (fallback text extraction) ───────────
            raw = _extract_with_pypdf2(pdf_bytes)
            if raw and raw.strip():
                text, score, was_broken = _process_candidate(raw)
                candidates.append((text, score, 'pypdf2', was_broken))
                logger.info(f"PyPDF2:  score={score}, broken={was_broken}")

            # Decide if OCR is needed
            # OCR if: no text at all, OR best candidate was broken, OR best score < 0.6
            best = max(candidates, key=lambda c: c[1]) if candidates else None
            need_ocr = (
                not best
                or best[1] < 0.6
                or best[3]  # was_broken — text needed reassembly
            )

            # ── Method 3: OCR (ultimate fallback) ────────────────────
            if need_ocr:
                logger.info("Trying OCR extraction...")
                raw = _extract_with_ocr(pdf_bytes)
                if raw and raw.strip():
                    text, score, was_broken = _process_candidate(raw)
                    candidates.append((text, score, 'ocr', was_broken))
                    logger.info(f"OCR:     score={score}, broken={was_broken}")

            if not candidates:
                return JsonResponse({
                    'success': False,
                    'error': 'PDF मध्ये काहीही मजकूर सापडला नाही. कृपया दुसरी PDF फाईल निवडा.'
                })

            # Pick best result
            best_text, best_score, best_method, _ = max(
                candidates, key=lambda c: c[1]
            )
            logger.info(f"Selected: {best_method} (score={best_score})")

            return JsonResponse({'success': True, 'text': best_text.strip()})

        except Exception as e:
            import traceback
            logger.error(f"PDF extraction error: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': f'PDF प्रक्रिया त्रुटी: {str(e)}'
            })

    return JsonResponse({'success': False, 'error': 'No PDF file provided'})


def _process_candidate(raw_text: str):
    """Reassemble broken text if needed and return (text, score, was_broken)."""
    was_broken = is_broken_devanagari(raw_text)
    if was_broken:
        text = reassemble_devanagari(raw_text)
    else:
        text = raw_text
    score = quality_score(text)
    return text, score, was_broken


def _extract_with_pymupdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF (fitz).

    PyMuPDF uses MuPDF under the hood which properly handles CIDFont
    ToUnicode CMaps — this gives much better Devanagari extraction
    than PyPDF2 for most PDFs.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            page_text = page.get_text("text") or ""
            if page_text.strip():
                pages.append(page_text)
        doc.close()
        return '\n\n'.join(pages)
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        return ""


def _extract_with_pypdf2(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        return '\n\n'.join(pages)
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
        return ""


def _extract_with_ocr(pdf_bytes: bytes) -> str:
    """Extract text from PDF using OCR (convert to images first)."""
    try:
        import pdf2image  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image as PILImage

        with tempfile.TemporaryDirectory() as path:
            pdf_pages = pdf2image.convert_from_bytes(
                pdf_bytes,
                dpi=300,
                output_folder=path
            )

            texts = []
            for page_num, page_image in enumerate(pdf_pages):
                logger.info(f"OCR processing page {page_num + 1}...")
                processed = preprocess_image_for_ocr(page_image)
                page_text = pytesseract.image_to_string(
                    processed,
                    config='--oem 1 --psm 6 -l mar+hin+san --dpi 300'
                )
                if page_text and page_text.strip():
                    texts.append(page_text.strip())

            return '\n\n'.join(texts)
    except ImportError as e:
        logger.warning(f"OCR dependencies not available: {e}")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""