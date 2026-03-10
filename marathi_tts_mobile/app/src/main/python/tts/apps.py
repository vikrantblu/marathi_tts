from django.apps import AppConfig
from django.conf import settings
import os
import threading
import time
import logging
from .utils.logging_config import setup_logging
from tts.utils.core.tts_settings import (
    TTS_TEMP_DIR, settings  # Only if you need access to other settings
)

logger = logging.getLogger(__name__)

class CleanupThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            try:
                self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            time.sleep(3600)  # Run every hour

    def cleanup_old_files(self):
        now = time.time()
        cleanup_count = 0

        for filename in os.listdir(TTS_TEMP_DIR):
            filepath = os.path.join(TTS_TEMP_DIR, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > settings.FILE_TTL:
                    try:
                        os.remove(filepath)
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"Failed to remove {filename}: {e}")

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} old files")

class TTSConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tts'
    _is_initialized = False

    def ready(self):
        # Only initialize once and skip in auto-reload subprocess
        if not self._is_initialized and os.environ.get('RUN_MAIN', None) == 'true':
            self._is_initialized = True
            from .utils.logging_config import setup_logging
            setup_logging()
            import logging
            logger = logging.getLogger('tts')
            logger.info('TTS application initialized')
