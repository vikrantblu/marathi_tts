import logging
import os
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from django.conf import settings

# Track initialized loggers to prevent duplication
_INITIALIZED_LOGGERS = set()
_SETUP_COMPLETE = False

def setup_logging(force=False):
    """Configure detailed logging for TTS system with single rotating file"""
    global _SETUP_COMPLETE

    # Skip if already initialized
    if _SETUP_COMPLETE and not force:
        return {}

    # Skip logging initialization in autoreloader subprocesses
    if os.environ.get('RUN_MAIN') != 'true':
        return {}

    try:
        # Create logs directory using absolute path
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Use a single log file with rotation
        main_log_file = os.path.join(log_dir, 'tts.log')

        # Ensure the log file exists
        if not os.path.exists(main_log_file):
            open(main_log_file, 'a').close()

        # Configure logging format with process ID
        formatter = logging.Formatter(
            '[%(asctime)s] [PID:%(process)d] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Rotating file handler with immediate flush
        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            delay=False
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Component loggers with their own handlers
        components = ['emotion', 'voice', 'audio', 'text', 'engine', 'views']
        loggers = {}

        for component in components:
            logger_name = f'tts.{component}'
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            # Create component-specific file handler
            component_file = os.path.join(log_dir, f'tts_{component}.log')
            component_handler = RotatingFileHandler(
                component_file,
                maxBytes=5 * 1024 * 1024,  # 5MB per component
                backupCount=3,
                encoding='utf-8',
                delay=False
            )
            component_handler.setFormatter(formatter)
            component_handler.setLevel(logging.DEBUG)

            logger.addHandler(component_handler)
            logger.addHandler(console_handler)
            loggers[logger_name] = logger

        # Log startup message to verify logging is working
        root_logger.info('Logging system initialized')
        for name, logger in loggers.items():
            logger.info(f'{name} logger initialized')

        # Mark setup as completed
        _SETUP_COMPLETE = True
        return loggers

    except Exception as e:
        # Print to console in case logging fails
        print(f"Error setting up logging: {str(e)}")
        raise

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

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent propagation to the root logger
    return logger