import os
import warnings

# ── Suppress noisy startup warnings before any third-party imports ────────────
# TensorFlow / XLA CUDA factory duplicate-registration messages
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
# absl-py "log messages before InitializeLog()" banner
os.environ.setdefault('GLOG_minloglevel', '3')
os.environ.setdefault('ABSL_LOGGING_LOG_TO_STDERR', '0')
# pydub ffmpeg-not-found warning (ffmpeg is optional; falls back gracefully)
warnings.filterwarnings('ignore', message="Couldn't find ffmpeg or avconv", category=RuntimeWarning)
# ─────────────────────────────────────────────────────────────────────────────

from pathlib import Path
import time
from datetime import datetime
from django.core.management.utils import get_random_secret_key

# Load .env file if present (development) — silently ignored if not found
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.management.commands.runserver import Command as RunserverCommand
import ssl
from django.core.servers.basehttp import WSGIServer, WSGIRequestHandler
from django.contrib.messages import constants as messages
import tempfile
import logging
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv('DJANGO_DEBUG', 'True') == 'True' else False

if DEBUG:
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_SSL_REDIRECT = False
    CSRF_COOKIE_SECURE = False
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_PROXY_SSL_HEADER = None
    SSL_CERTIFICATE = str(BASE_DIR / 'cert.pem')
    SSL_KEY = str(BASE_DIR / 'key.pem')
    class SSLWSGIServer(WSGIServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(
                certfile=os.path.join(BASE_DIR, 'cert.pem'),
                keyfile=os.path.join(BASE_DIR, 'key.pem')
            )
            self.socket = context.wrap_socket(
                self.socket,
                server_side=True
            )

    class SSLWSGIRequestHandler(WSGIRequestHandler):
        def handle(self):
            self.request.settimeout(60)  # Increased timeout
            super().handle()
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

    # Add these for service worker support in development
    PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/tts/js/common', 'service-worker.js')
    PWA_APP_SCOPE = '/marathi_tts/'
    PWA_APP_START_URL = '/marathi_tts/tts/'
else:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Add environment check helper
def is_development():
    return DEBUG and not any([
        os.environ.get('PRODUCTION'),
        os.environ.get('STAGING')
    ])

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# ALLOWED_HOSTS — set DJANGO_ALLOWED_HOSTS=host1,host2 in your .env or environment
_allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,[::1],0.0.0.0')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]

# CSRF trusted origins — set CSRF_TRUSTED_ORIGINS=https://yourdomain.com in your environment
_csrf_origins_env = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:9000,http://127.0.0.1:9000,http://localhost:8888,http://127.0.0.1:8888,http://localhost:8001,http://127.0.0.1:8001'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins_env.split(',') if o.strip()]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Adjust logging level to reduce verbose output

# Update the LOGGING configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{process:d}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'tts_debug.log'),
            'formatter': 'verbose',
            'mode': 'a',  # append mode
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'tts': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'models': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Add this to control reloading
if DEBUG:
    import sys
    if (len(sys.argv) > 1 and sys.argv[1] == 'runserver'):
        # Reduce auto-reload sensitivity
        import django.utils.autoreload
        django.utils.autoreload.RELOAD_TIMEOUT = 2  # seconds

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add this at the top
    'marathi_tts.middleware.LoggingInitMiddleware',
    'marathi_tts.middleware.CleanupMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'marathi_tts.middleware.JavaScriptModuleMiddleware'
]

ROOT_URLCONF = 'marathi_tts.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'tts', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'marathi_tts.wsgi.application'

# ASGI configuration
ASGI_APPLICATION = 'marathi_tts.asgi.application'

# For development server
DJANGO_ALLOW_ASYNC_UNSAFE = True  # Only for development

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Add proper MIME type for JS modules
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Dev runserver SSL — enabled by default when cert files exist.
# Set DJANGO_DEV_SSL=False to disable and use plain HTTP.
_dev_ssl_enabled = os.getenv('DJANGO_DEV_SSL', 'False') == 'True'
if _dev_ssl_enabled and os.path.exists(os.path.join(BASE_DIR, 'cert.pem')) and os.path.exists(os.path.join(BASE_DIR, 'key.pem')):
    RunserverCommand.server_cls = SSLWSGIServer
    RunserverCommand.handler_cls = SSLWSGIRequestHandler

# CORS — set CORS_ALLOWED_ORIGINS=https://yourdomain.com in your environment
CORS_ALLOW_CREDENTIALS = True
_cors_origins_env = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:9000,http://127.0.0.1:9000,http://localhost:8888,http://127.0.0.1:8888,http://localhost:8001,http://127.0.0.1:8001'
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(',') if o.strip()]
CORS_ORIGIN_WHITELIST = CSRF_TRUSTED_ORIGINS

# Tesseract Configuration
# On Linux/WSL, Tesseract is available in PATH, so we don't need to specify the path
TESSERACT_LANGUAGE = os.getenv('TESSERACT_LANGUAGE', 'mar')

# Development SSL settings
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_HOST = None
    
    # Allow unsafe requests to external services during development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Add development-specific middleware if needed
    MIDDLEWARE = [m for m in MIDDLEWARE if m != 'django.middleware.security.SecurityMiddleware'] + \
                 ['django.middleware.security.SecurityMiddleware']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',  # Add this
    'tts.apps.TTSConfig',  # Your TTS app
]

INDIC_NLP_RESOURCES = os.getenv('INDIC_NLP_RESOURCES', os.path.join(BASE_DIR, 'indic_nlp_resources'))
INDIC_NLP_LIB = os.getenv('INDIC_NLP_LIB', os.path.join(BASE_DIR, 'indic_nlp_library'))

import sys
sys.path.append(INDIC_NLP_LIB)
