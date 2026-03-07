import os
from pydub import AudioSegment
import tempfile
import logging

logger = logging.getLogger('tts.audio')

# Global audio cache to avoid redundant ffmpeg conversions
_audio_cache = {}

def load_audio(filepath: str, max_cache_size: int = 50) -> AudioSegment:
    """Load audio with caching to reduce ffmpeg calls"""
    global _audio_cache
    
    if filepath in _audio_cache:
        return _audio_cache[filepath]
    
    # If cache is too large, clear it
    if len(_audio_cache) > max_cache_size:
        _audio_cache.clear()
    
    # Determine format from extension
    ext = os.path.splitext(filepath)[1].lower()[1:]
    if ext == 'mp3':
        audio = AudioSegment.from_mp3(filepath)
    elif ext == 'wav':
        audio = AudioSegment.from_wav(filepath)
    else:
        audio = AudioSegment.from_file(filepath)
    
    # Cache the result
    _audio_cache[filepath] = audio
    return audio