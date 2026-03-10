"""
Security utilities — URL validation, path sanitization, input limits.
"""
import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL validation (SSRF prevention)
# ---------------------------------------------------------------------------

# Blocked IP ranges: private, loopback, link-local, reserved, metadata
_BLOCKED_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),  # AWS/Azure/GCP metadata
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
    ipaddress.ip_network('0.0.0.0/8'),
]


def is_safe_url(url: str) -> bool:
    """Validate URL is safe for server-side fetch (anti-SSRF).

    Returns True only when:
    - scheme is http or https
    - hostname resolves to a public (non-private) IP
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            logger.warning("Blocked URL with scheme: %s", parsed.scheme)
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        except socket.gaierror:
            logger.warning("DNS resolution failed for: %s", hostname)
            return False

        for family, _type, _proto, _canon, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                logger.warning("Blocked private/reserved IP %s for host %s", ip, hostname)
                return False
            for blocked in _BLOCKED_RANGES:
                if ip in blocked:
                    logger.warning("Blocked IP %s in range %s for host %s", ip, blocked, hostname)
                    return False

        return True
    except Exception as exc:
        logger.warning("URL validation failed for %s: %s", url, exc)
        return False


# ---------------------------------------------------------------------------
# Path sanitization
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(r'^[a-f0-9\-]{1,64}$')
_SAFE_FILENAME_RE = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


def is_safe_session_id(session_id: str) -> bool:
    """Validate session_id is a safe identifier (alphanumeric/UUID)."""
    return bool(_UUID_RE.match(session_id))


def is_safe_filename(name: str) -> bool:
    """Validate filename has no path traversal characters."""
    return bool(_SAFE_FILENAME_RE.match(name)) and '..' not in name


def is_path_within(filepath: str, base_dir: str) -> bool:
    """Check that resolved filepath stays within base_dir."""
    import os
    real_file = os.path.realpath(filepath)
    real_base = os.path.realpath(base_dir)
    return real_file.startswith(real_base + os.sep) or real_file == real_base


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------

# Magic byte signatures for allowed image formats
_IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'BM': 'image/bmp',
}

MAX_IMAGE_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_UPLOAD_SIZE = 50 * 1024 * 1024    # 50 MB
MAX_AUDIO_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_TEXT_INPUT_LENGTH = 100_000            # characters


def validate_image_upload(file_obj) -> str | None:
    """Validate uploaded image. Returns error string or None if valid."""
    if file_obj.size > MAX_IMAGE_UPLOAD_SIZE:
        return f'File too large (max {MAX_IMAGE_UPLOAD_SIZE // (1024*1024)} MB)'

    # Check magic bytes
    header = file_obj.read(4)
    file_obj.seek(0)
    for sig in _IMAGE_SIGNATURES:
        if header[:len(sig)] == sig:
            return None  # Valid

    return 'Invalid image format — only JPEG, PNG, and BMP accepted'


def validate_pdf_upload(file_obj) -> str | None:
    """Validate uploaded PDF. Returns error string or None if valid."""
    if file_obj.size > MAX_PDF_UPLOAD_SIZE:
        return f'File too large (max {MAX_PDF_UPLOAD_SIZE // (1024*1024)} MB)'

    header = file_obj.read(5)
    file_obj.seek(0)
    if not header.startswith(b'%PDF-'):
        return 'Invalid PDF file'

    return None


def validate_audio_upload(file_obj) -> str | None:
    """Validate uploaded audio. Returns error string or None if valid."""
    if file_obj.size > MAX_AUDIO_UPLOAD_SIZE:
        return f'File too large (max {MAX_AUDIO_UPLOAD_SIZE // (1024*1024)} MB)'
    return None
