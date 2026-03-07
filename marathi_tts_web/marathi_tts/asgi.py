"""
ASGI config for marathi_tts project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
from django.contrib.staticfiles.handlers import StaticFilesHandler

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('TRANSFORMERS_NO_TF', '1')
os.environ.setdefault('USE_TF', '0')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marathi_tts.settings')

application = StaticFilesHandler(get_wsgi_application())