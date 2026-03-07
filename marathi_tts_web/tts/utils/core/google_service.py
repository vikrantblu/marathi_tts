from .base_service import TTSBaseService
from gtts import gTTS
from gtts.tokenizer import pre_processors, Tokenizer
import os
import logging
from tts.constants.tts_config import SUPPORTED_LANGUAGES

logger = logging.getLogger('tts.text')

class CachedGTTS(gTTS):
    """A custom gTTS implementation that avoids redundant language validation"""
    
    # Cache of valid languages (from centralized constants)
    _VALID_LANGUAGES = {k: True for k in SUPPORTED_LANGUAGES}
    _LANGUAGE_NAMES = SUPPORTED_LANGUAGES
    
    def __init__(self, text, lang='mr', slow=False, **kwargs):
        """Initialize with minimal validation"""
        # Force lang_check=False to skip validation
        super().__init__(text, lang=lang, slow=slow, lang_check=False, **kwargs)
        
        # Skip tokenization pre-processing if text is very short
        if len(text) < 50:
            self.tokenizer = Tokenizer([])  # No pre-processors for short text
    
    def _fetch_langs(self):
        """Skip the HTTP call to fetch languages"""
        return self._LANGUAGE_NAMES
    
    def _validate_lang(self, lang):
        """Only validate the languages we care about"""
        if lang not in self._VALID_LANGUAGES:
            logger.warning(f"Language {lang} not explicitly supported, defaulting to Marathi")
            return 'mr'
        return lang

class GoogleTTSService(TTSBaseService):
    """Google TTS implementation"""
    
    def generate_speech(self, text: str, **kwargs):
        try:
            tts = CachedGTTS(text=text, lang='mr')
            temp_mp3 = "temp.mp3"
            tts.save(temp_mp3)
            return temp_mp3
        except Exception as e:
            logger.error(f"Google TTS error: {str(e)}")
            raise