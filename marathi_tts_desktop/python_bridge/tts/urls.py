import json
import logging
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import tts_views
from .views import ocr_image_view, website_view
from .views.ocr_pdf_view import extract_pdf_text
from .views import ai_view  # Import the correct view module
from .views.ai_view import suggest_correction
from .views.stt_view import transcribe_audio
from .views.script_convert_view import convert_script
from .views.stotra_view import stotra_list, stotra_text

logger = logging.getLogger(__name__)

app_name = 'tts'

urlpatterns = [
    path('', tts_views.tts_home, name='home'),
    path('generate-audio/', tts_views.generate_tts, name='generate_audio'),
    path('fetch-content/', website_view.fetch_website_content, name='fetch_content'),
    path('error/', tts_views.error_page, name='error'),
    path('cleanup/', tts_views.cleanup_temp_files, name='cleanup'),
    path('fetch-website-content/', website_view.fetch_website_content, name='fetch_website_content'),
    path('extract-text/', ocr_image_view.extract_text_from_image, name='extract_text'),
    path('analyze-emotion/', tts_views.analyze_emotion, name='analyze_emotion'),
    path('stream-status/<str:session_id>/', tts_views.stream_status, name='stream_status'),
    path('extract-pdf-text/', extract_pdf_text, name='extract_pdf_text'),
    path('generate-audio/stream/', tts_views.generate_audio_streaming, name='generate_audio_streaming'),
    path('api/correct-text-para/', ai_view.correct_text_para, name='correct-text-para'),
    path('api/format-text/', ai_view.format_text, name='format-text'),
    path('tts/suggest-correction/', suggest_correction, name='suggest_correction'),
    # Speech-to-Text
    path('api/transcribe-audio/', transcribe_audio, name='transcribe_audio'),
    # Script Converter (Modi / IAST / Brahmi ↔ Devanagari)
    path('api/convert-script/', convert_script, name='convert_script'),
    # Stotra Library
    path('api/stotras/', stotra_list, name='stotra_list'),
    path('api/stotras/<int:stotra_id>/', stotra_text, name='stotra_text'),
]
