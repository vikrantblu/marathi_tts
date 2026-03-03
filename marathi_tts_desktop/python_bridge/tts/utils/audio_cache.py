"""
TTS Audio Cache
================
Hash-based audio caching for TTS-generated audio files. Avoids redundant
gTTS/edge-tts API calls for identical text+params combinations.

Usage:
    from tts.utils.audio_cache import AudioCache

    cache = AudioCache(cache_dir='/path/to/cache', max_size_mb=50)

    # Check cache before generating
    key = cache.make_key(text, engine='gtts', lang='mr', speed=1.0)
    cached = cache.get(key)
    if cached:
        return cached  # audio file path

    # Generate audio...
    generate_audio(text, output_path)

    # Store in cache
    cache.put(key, output_path)
"""
import os
import hashlib
import shutil
import time
import logging
from typing import Optional

logger = logging.getLogger('tts.cache')

# Default cache size limit
DEFAULT_MAX_SIZE_MB = 50


class AudioCache:
    """LRU-evicting file cache for TTS audio.

    Cache keys are SHA-256 hashes of (text + engine + params).
    Files are stored as `<hash>.mp3` in the cache directory.
    When the cache exceeds max_size_mb, oldest files are evicted.
    """

    def __init__(self, cache_dir: str, max_size_mb: int = DEFAULT_MAX_SIZE_MB):
        """
        Args:
            cache_dir: Directory to store cached audio files.
            max_size_mb: Maximum total cache size in megabytes.
        """
        self._cache_dir = cache_dir
        self._max_size_bytes = max_size_mb * 1024 * 1024
        os.makedirs(cache_dir, exist_ok=True)

    @staticmethod
    def make_key(text: str, engine: str = 'gtts', lang: str = 'mr',
                 speed: float = 1.0, pitch: float = 1.0,
                 voice: str = '', is_verse: bool = False) -> str:
        """Generate a deterministic cache key from TTS parameters.

        Returns a hex SHA-256 digest string.
        """
        key_str = f"{text}|{engine}|{lang}|{speed:.2f}|{pitch:.2f}|{voice}|{is_verse}"
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

    def get(self, key: str) -> Optional[str]:
        """Look up a cached audio file by key.

        Returns the file path if found, None otherwise.
        Updates the file's mtime to keep it fresh (LRU).
        """
        path = os.path.join(self._cache_dir, f"{key}.mp3")
        if os.path.isfile(path):
            # Touch mtime for LRU tracking
            try:
                os.utime(path, None)
            except OSError:
                pass
            logger.debug("Cache HIT: %s", key[:12])
            return path
        return None

    def put(self, key: str, source_path: str) -> Optional[str]:
        """Copy an audio file into the cache.

        Args:
            key: Cache key (from make_key).
            source_path: Path to the generated audio file.

        Returns the cache file path, or None on failure.
        """
        if not os.path.isfile(source_path):
            return None

        dest = os.path.join(self._cache_dir, f"{key}.mp3")
        try:
            shutil.copy2(source_path, dest)
            logger.debug("Cache PUT: %s (%d bytes)",
                         key[:12], os.path.getsize(dest))
            self._evict_if_needed()
            return dest
        except Exception as exc:
            logger.warning("Cache PUT failed: %s", exc)
            return None

    def _evict_if_needed(self):
        """Evict oldest files if total cache size exceeds the limit."""
        try:
            files = []
            total_size = 0
            for name in os.listdir(self._cache_dir):
                fpath = os.path.join(self._cache_dir, name)
                if not os.path.isfile(fpath):
                    continue
                stat = os.stat(fpath)
                files.append((fpath, stat.st_mtime, stat.st_size))
                total_size += stat.st_size

            if total_size <= self._max_size_bytes:
                return

            # Sort by mtime ascending (oldest first = least recently used)
            files.sort(key=lambda x: x[1])
            evicted = 0
            for fpath, _, fsize in files:
                if total_size <= self._max_size_bytes:
                    break
                try:
                    os.unlink(fpath)
                    total_size -= fsize
                    evicted += 1
                except OSError:
                    pass

            if evicted:
                logger.info("Cache evicted %d files (%.1f MB remaining)",
                            evicted, total_size / (1024 * 1024))
        except Exception as exc:
            logger.warning("Cache eviction error: %s", exc)

    def clear(self):
        """Remove all cached files."""
        try:
            for name in os.listdir(self._cache_dir):
                fpath = os.path.join(self._cache_dir, name)
                if os.path.isfile(fpath):
                    os.unlink(fpath)
            logger.info("Cache cleared")
        except Exception as exc:
            logger.warning("Cache clear failed: %s", exc)

    @property
    def size_mb(self) -> float:
        """Current total cache size in MB."""
        total = 0
        try:
            for name in os.listdir(self._cache_dir):
                fpath = os.path.join(self._cache_dir, name)
                if os.path.isfile(fpath):
                    total += os.path.getsize(fpath)
        except OSError:
            pass
        return total / (1024 * 1024)
