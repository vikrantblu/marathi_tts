#!/usr/bin/env python3
"""
Web Bridge - Marathi Website Content Fetcher
============================================
Fetches and extracts Marathi text content from a URL.

Usage:
    python web_bridge.py --url https://example.com

Returns: JSON { success, text, title, image_texts_count }
"""

import sys, os, json, argparse, traceback, time, re
import urllib3  # type: ignore
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
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
        log.info("HTTP %d | %.2fs | encoding=%s | content_len=%d",
                 resp.status_code, time.time() - t_req,
                 resp.encoding, len(resp.content))

        # Handle encoding
        if resp.encoding and resp.encoding.lower() != "iso-8859-1":
            html = resp.text
        else:
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        # Remove noise tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form",
                         "noscript", "iframe"]):
            tag.decompose()

        # Title
        title_tag = soup.find("title") or soup.find("h1") or soup.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else ""
        log.info("Page title extracted | len=%d", len(title))

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

        # Image OCR — skipped on mobile (PIL/pytesseract unavailable)
        image_texts = []
        try:
            import PIL  # noqa: F401
            _has_pil = True
        except ImportError:
            _has_pil = False
        if process_images and _has_pil:
            img_tags = soup.find_all("img", src=True)[:5]
            log.info("Processing %d images for OCR", len(img_tags))
            for img_tag in img_tags:
                ocr_text = _ocr_image_url(img_tag["src"], url)
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
