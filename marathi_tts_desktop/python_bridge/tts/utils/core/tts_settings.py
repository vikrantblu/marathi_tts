import os
import time
import logging
from pathlib import Path
from django.conf import settings as django_settings
from functools import lru_cache

# Configure logger
logger = logging.getLogger('tts')

# Initialize only when needed, not at module import
_singleton_instance = None

class TTSSettings:
    def __init__(self):
        self._config = None
        self._initialized = False
        
    def _load_settings(self):
        """Load settings only if not already initialized"""
        if not self._initialized:
            # Django settings attributes
            self.MEDIA_ROOT = django_settings.MEDIA_ROOT
            self.BASE_DIR = django_settings.BASE_DIR
            self.MEDIA_URL = django_settings.MEDIA_URL
            
            # TTS specific settings (from centralized constants)
            self._config = TTS_DEFAULTS.copy()
            self._initialized = True
            
            # Only log for certain commands (skip for checks/migrations)
            command = os.environ.get('DJANGO_COMMAND', '')
            if command not in ['makemigrations', 'migrate', 'collectstatic', 'check']:
                logger.info(f"[PID:{os.getpid()}] TTSSettings initialized")

    def __getattr__(self, name):
        if not self._initialized:
            self._load_settings()
            
        if hasattr(self, '_config') and name in self._config:
            return self._config[name]
        
        raise AttributeError(f"'Settings' object has no attribute '{name}'")

    @property
    def config(self):
        if not self._initialized:
            self._load_settings()
        return self._config.copy()

# Lazy initialization function
def get_settings():
    global _singleton_instance
    if _singleton_instance is None:
        _singleton_instance = TTSSettings()
    return _singleton_instance

# Lazy properties
@property
def MAX_TEXT_LENGTH():
    return get_settings().MAX_TEXT_LENGTH

@property
def SAMPLE_RATE():
    return get_settings().SAMPLE_RATE

@property
def AUDIO_FORMAT():
    return get_settings().AUDIO_FORMAT

@property
def FRAME_RATE():
    return get_settings().FRAME_RATE

from tts.constants.script_constants import SCRIPT_RANGES as _IMPORTED_SCRIPT_RANGES
from tts.constants.tts_config import TTS_DEFAULTS

# Define script ranges directly (from centralized constants)
SCRIPT_RANGES = _IMPORTED_SCRIPT_RANGES

# Define paths - but don't initialize directories yet
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Initialize settings instance lazily
settings = get_settings()

# Define media paths without accessing settings immediately
TTS_MEDIA_URL = django_settings.MEDIA_URL + 'tts/'
TTS_MEDIA_ROOT = os.path.join(django_settings.MEDIA_ROOT, 'tts')
TTS_TEMP_DIR = os.path.join(TTS_MEDIA_ROOT, 'temp')
TTS_CACHE_DIR = os.path.join(TTS_MEDIA_ROOT, 'cache')
TTS_LOG_DIR = LOGS_DIR

# Required directories - defined but not created yet
REQUIRED_DIRS = [
    TTS_MEDIA_ROOT,
    TTS_TEMP_DIR,
    TTS_CACHE_DIR,
    TTS_LOG_DIR
]

# Only initialize directories when explicitly called
def initialize_directories():
    """Initialize all required directories with proper permissions"""
    for directory in REQUIRED_DIRS:
        try:
            os.makedirs(directory, exist_ok=True)
            if os.name == 'posix':
                os.chmod(directory, 0o755)
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
            raise

# Don't call initialize_directories() at module import time!