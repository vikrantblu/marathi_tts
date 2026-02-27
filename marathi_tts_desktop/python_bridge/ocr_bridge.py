#!/usr/bin/env python3
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
