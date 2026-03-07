from tts.utils.logging_config import setup_logging
import logging
from logging.handlers import RotatingFileHandler
import os
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('tts.middleware')

class JavaScriptModuleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.endswith('.js'):
            response['Content-Type'] = 'application/javascript'
        return response

class LoggingInitMiddleware:
    """Middleware that ensures logging is properly set up."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._logging_initialized = False
        # Ensure logs directory exists
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        
    def __call__(self, request):
        # Initialize logging if not already done
        if not self._logging_initialized:
            from tts.utils.logging_config import setup_logging
            setup_logging()
            self._logging_initialized = True
            
        response = self.get_response(request)
        return response

class CleanupMiddleware:
    """Middleware that occasionally cleans up old files during requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_cleanup = None
        self.cleanup_interval = 3600  # 1 hour
        
    def __call__(self, request):
        # Only check occasionally to avoid overhead
        import random
        import time
        from datetime import datetime
        
        now = time.time()
        
        # Only run cleanup rarely (1% of requests) and only if enough time has passed
        if (random.random() < 0.01 and 
            (self.last_cleanup is None or (now - self.last_cleanup > self.cleanup_interval))):
            
            try:
                from django.core.management import call_command
                call_command('cleanup_temp_files', '--all')
                self.last_cleanup = now
                print(f"[{datetime.now()}] Ran scheduled cleanup via middleware")
            except Exception as e:
                print(f"Cleanup error in middleware: {str(e)}")
            
        response = self.get_response(request)
        return response

class TTSErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            logger.error(f"TTS Error: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'TTS Engine Error',
                'detail': str(e)
            }, status=500)

def get_logger(name):
    """Get a logger instance with duplicate initialization protection"""
    logger = logging.getLogger(name)

    # Check if handlers are already attached to avoid duplicates
    if not logger.handlers:
        # Add handlers only if none exist
        formatter = logging.Formatter(
            '[%(asctime)s] [PID:%(process)d] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = RotatingFileHandler(
            os.path.join(settings.BASE_DIR, 'logs', f'{name}.log'),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8',
            delay=False
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Add a console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent propagation to the root logger
    return logger