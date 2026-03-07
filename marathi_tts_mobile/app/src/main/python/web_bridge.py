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
# urllib3 warning suppression removed for security — TLS errors should be visible

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


def _is_safe_url(url: str) -> bool:
    """Reject private/internal IPs and non-HTTP schemes to prevent SSRF."""
    try:
        from urllib.parse import urlparse
        import ipaddress, socket
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for _fam, _type, _proto, _canon, addr in resolved:
                ip = ipaddress.ip_address(addr[0])
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "mr,hi;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# Special site handlers — for JS-heavy sites that embed content in <script>
# ---------------------------------------------------------------------------

def _try_abhyaskosh(html: str, url: str) -> str:
    """Extract Jnaneshwari / Gita content from abhyaskosh.org.

    This site renders content via JavaScript from inline JSON variables
    (adhyayStr, shlokaStr, oviStr).  BeautifulSoup cannot see the rendered
    DOM, so we parse the JSON directly from the HTML source.
    """
    import json as _json

    lines = []

    # Extract chapter metadata
    m = re.search(r'var\s+adhyayStr\s*=\s*(\{.*?\});', html, re.DOTALL)
    if m:
        try:
            data = _json.loads(m.group(1))
            entries = data.get('data', [])
            if entries:
                e = entries[0]
                intro = e.get('introduction', '')
                subject = e.get('subject', '')
                if intro:
                    lines.append(intro)
                if subject:
                    lines.append(subject)
        except (ValueError, KeyError):
            pass

    # Extract Ovis (Jnaneshwari verses) — primary content
    m = re.search(r'var\s+oviStr\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
    if m:
        try:
            data = _json.loads(m.group(1))
            for ovi in data.get('data', []):
                text = ovi.get('text', '').strip()
                if text:
                    lines.append(text)
        except (ValueError, KeyError):
            pass

    # Extract Shlokas (Gita verses embedded with chapter)
    m = re.search(r'var\s+shlokaStr\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
    if m:
        raw_json = m.group(1)
        raw_json = re.sub(r',\s*([}\]])', r'\1', raw_json)
        try:
            data = _json.loads(raw_json)
            for shloka in data.get('data', []):
                text = shloka.get('text', '').strip()
                if text:
                    lines.append(text)
        except (ValueError, KeyError):
            pass

    # Extract chapter conclusion
    try:
        m2 = re.search(r'var\s+adhyayStr\s*=\s*(\{.*?\});', html, re.DOTALL)
        if m2:
            data = _json.loads(m2.group(1))
            entries = data.get('data', [])
            if entries:
                conclusion = entries[0].get('conclusion', '')
                if conclusion:
                    lines.append(conclusion)
    except Exception:
        pass

    result = '\n'.join(lines)
    log.info("[abhyaskosh] Extracted %d lines, %d chars", len(lines), len(result))
    return result


def _is_abhyaskosh_url(url: str) -> bool:
    """Check if URL belongs to abhyaskosh.org."""
    return 'abhyaskosh.org' in url.lower()


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

    # SSRF prevention: reject private/internal IPs
    if not _is_safe_url(url):
        log.warning("Blocked unsafe URL: %s", url[:100])
        return {"success": False, "error": "URL is blocked (private/internal address)"}

    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:
        log.error("Missing dependency: %s. Run: pip install requests beautifulsoup4", exc)
        return {"success": False, "error": f"Missing package: {exc}"}

    try:
        log.info("HTTP GET %s", url)
        t_req = time.time()
        resp = requests.get(url, headers=_HEADERS, timeout=20, verify=True)
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

        # ── Special site handlers (JS-heavy sites) ────────────────────
        if _is_abhyaskosh_url(url):
            special_text = _try_abhyaskosh(html, url)
            if special_text and len(special_text) > 50:
                log.info("[Special] abhyaskosh.org handler extracted %d chars", len(special_text))
                try:
                    from bs4 import BeautifulSoup as _BS
                    _soup = _BS(html, "html.parser")
                    _title_tag = _soup.find("title")
                    title = _title_tag.get_text(strip=True) if _title_tag else ""
                except Exception:
                    title = ""
                cleaned_text = _clean_text(special_text)
                if title:
                    cleaned_text = f"{title}\n\n{cleaned_text}"
                return {
                    "success": True, "text": cleaned_text, "title": title,
                    "image_texts_count": 0,
                    "char_count": len(cleaned_text),
                    "elapsed_sec": round(time.time() - t0, 2),
                }

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
