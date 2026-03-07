from django.conf import settings
from functools import wraps
import os
import logging
import traceback
from bs4 import BeautifulSoup
import requests
import unicodedata
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from pydub import AudioSegment # type: ignore
from tts.utils.core.tts_settings import settings

from ..utils.text.script_converter import modi_to_devanagari

from ..utils.core.tts_engine import TTSEngine
from django.shortcuts import render

import json
import time as time_module  

from ..utils.core import generate_tts_audio
from ..utils.emotion.emotion_analyzer import EmotionAnalyzer

from django.http import JsonResponse, StreamingHttpResponse
import re
import uuid
from urllib.parse import urljoin
import tempfile
from PIL import Image
import io
# pytesseract removed - not used in this file

from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect, csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework.decorators import api_view # type: ignore
from rest_framework.response import Response # type: ignore
from django.http import JsonResponse
from ..utils.text.text_processor import is_devnagari_text, detect_script, clean_text
# Add this at the module level
from functools import lru_cache
import hashlib
from ..utils.text.text_normalizer import MarathiTextNormalizer
from ..utils.core.tts_service import TTSService
from asgiref.sync import sync_to_async, async_to_sync
from django.utils.decorators import sync_and_async_middleware

logger = logging.getLogger(__name__)
logger = logging.getLogger('tts.views')

# Update the rate limit decorator to support async
def rate_limit(key_prefix, limit=10, period=60):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped(request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR', '')
            cache_key = f"ratelimit:{key_prefix}:{client_ip}"
            
            # Convert cache operations to async
            request_count = await sync_to_async(cache.get)(cache_key, 0)
            
            if request_count >= limit:
                logger.warning(f"Rate limit exceeded for {client_ip} on {key_prefix}")
                return JsonResponse({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            
            if request_count == 0:
                await sync_to_async(cache.set)(cache_key, 1, period)
            else:
                await sync_to_async(cache.incr)(cache_key)
            
            return await view_func(request, *args, **kwargs)
        return wrapped
    return decorator

# Views
@login_required
def entry_page(request):
    return render(request, 'kundali/entry_page.html')

def error_page(request):
    return render(request, 'tts/error.html')

def cleanup_temp_files(request):
    """Clean up old temporary audio files"""
    media_dir = os.path.join(settings.MEDIA_ROOT, 'tts')
    deleted = 0
    now = datetime.now()
    
    try:
        for filename in os.listdir(media_dir):
            filepath = os.path.join(media_dir, filename)
            # Check if file is older than 24 hours
            file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            if now - file_modified > timedelta(hours=24):
                os.remove(filepath)
                deleted += 1
                
        return JsonResponse({
            'success': True,
            'message': f'Deleted {deleted} old files',
            'deleted': deleted
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def tts_home(request):
    """Render the TTS interface"""
    context = {
        'max_text_length': settings.MAX_TEXT_LENGTH,  # Updated from MAX_TEXT_LENGTH
        'available_voices': [
            {'id': 'google', 'name': 'Google TTS'},
            {'id': 'arohi', 'name': 'अरोही (स्त्री)'},
            {'id': 'manohar', 'name': 'मनोहर (पुरुष)'}
        ]
    }
    return render(request, 'tts/tts_home.html', context)

# Add emotion detection class
class EmotionDetector:
    def __init__(self):
        self.emotion_patterns = {
            'happy': r'[!।]+|हा हा|खुश|आनंद|सुख|हर्ष|उल्हास|उत्साह|मजा|गंमत|खेळकर|रंगेल|मौज|धमाल|सुखी|प्रसन्न',
            'sad': r'दु:ख|काळजी|चिंता|शोक|खेद|व्यथा|दुर्दैव|दैन्य|कष्ट|त्रास|वेदना|रडणे|विषाद|उदास|हताश|निराश',
            'angry': r'राग|क्रोध|चीड|संताप|रोष|आक्रोश|कोप|तावातावाने|चिडून|रागावून|अश्लील|घृणा|द्वेष',
            'fear': r'भय|भीती|दहशत|धास्ती|घाबरणे|दचकणे|भयभीत|धाक|धमकी|त्रास|संकट',
            'surprise': r'आश्चर्य|विस्मय|चकित|अचंबित|थक्क|दचकणे|चमत्कार|अनपेक्षित|अचानक',
            'neutral': r'.',  # Default pattern
            'peaceful': r'शांत|समाधान|स्थिर|निवांत|सुस्थिर|शांतता|विश्रांती|निर्मळ|स्वच्छ|मोकळे',
            'devotional': r'भक्ती|प्रार्थना|विनंती|स्तुती|आराधना|पूजा|नमन|वंदन|जप|ध्यान|समर्पण'
        }

class AudioProcessor:
    def __init__(self):
        self.sample_rate = 22050
        self.channels = 1

    async def process_chunks(self, audio_segments):
        combined = AudioSegment.empty()
        for segment in audio_segments:
            combined += AudioSegment.from_file(segment)
        return combined
    
    def detect_emotion(self, text):
        emotions = {}
        for emotion, pattern in self.emotion_patterns.items():
            matches = len(re.findall(pattern, text))
            emotions[emotion] = matches
        
        # Normalize scores
        total = sum(emotions.values()) or 1
        return {k: v/total for k, v in emotions.items()}
    
@csrf_protect
@rate_limit('tts_gen', limit=10, period=60)
async def generate_tts(request):
    """Unified TTS generation supporting both sync and async modes"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        text = data.get('text', '').strip()
        use_streaming = data.get('streaming', False)
        use_advanced = data.get('advanced', False)
        language = data.get('language', 'mr')
        engine_choice = data.get('engine', 'auto')
        gender = data.get('gender', 'female')
        is_verse = data.get('verse_mode', False)
        
        if use_streaming:
            return await handle_streaming_tts(text, use_advanced)
            
        elif use_advanced:
            tts_service = TTSService()
            result = await tts_service.generate_speech(
                text=text,
                user_id=request.user.id if request.user.is_authenticated else None
            )
            
            return JsonResponse({
                'success': True,
                'audio_url': result['audio_url'],
                'analysis': result['analysis'],
                'phonetic_data': result['phonetic_data']
            })
        else:
            # Convert sync operations to async
            engine = TTSEngine()
            
            # Voice params — pass language, engine, gender, and verse mode
            voice_params = {
                'language': language,
                'engine': engine_choice,
                'gender': gender,
                'verse_mode': is_verse,
            }
            
            # Engine handles normalization + emotion + prosody internally
            audio_path = await sync_to_async(engine.generate_tts_audio)(
                text=text,
                voice_params=voice_params
            )

            if not audio_path or not os.path.exists(audio_path):
                raise FileNotFoundError("Failed to generate audio file")
                
            audio_url = f'/media/tts/{os.path.basename(audio_path)}'
            return JsonResponse({
                'success': True,
                'audio_url': audio_url,
                'filename': os.path.basename(audio_path)
            })

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON request'
        }, status=400)
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_streaming_tts(text: str, use_advanced: bool):
    """Handle streaming TTS generation"""
    try:
        chunk_size = 1000  # characters per chunk
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        
        async def generate():
            for chunk in chunks:
                if use_advanced:
                    tts_service = TTSService()
                    result = await tts_service.generate_speech(chunk)
                    yield json.dumps({
                        'chunk': result['audio_url'],
                        'analysis': result['analysis']
                    }) + '\n'
                else:
                    @sync_to_async
                    def process_chunk():
                        engine = TTSEngine()
                        normalizer = MarathiTextNormalizer()
                        return engine.generate_tts_audio(
                            text=normalizer.normalize_text(chunk)
                        )
                    
                    audio_path = await process_chunk()
                    audio_url = f'/media/tts/{os.path.basename(audio_path)}'
                    yield json.dumps({
                        'chunk': audio_url
                    }) + '\n'

        return StreamingHttpResponse(
            generate(), 
            content_type='application/x-ndjson'
        )
        
    except Exception as e:
        logger.error(f"Streaming TTS failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_protect
@rate_limit('tts_gen', limit=10, period=60)
def combine_audio_segments(segments):
    """Combine multiple audio segments into a single file"""
    combined = AudioSegment.empty()
    for segment in segments:
        combined += AudioSegment.from_file(segment)
    
    # Save combined audio
    output_path = os.path.join(settings.MEDIA_ROOT, 'tts', f'combined_{uuid.uuid4()}.mp3')
    combined.export(output_path, format='mp3')
    return output_path
@ensure_csrf_cookie
@require_http_methods(["POST"])
def analyze_emotion(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({
                'error': 'Text is required'
            }, status=400)

        # Initialize emotion analyzer
        analyzer = EmotionAnalyzer()
        
        # Analyze text
        result = analyzer.analyze(text)
        
        return JsonResponse({
            'dominant': result['dominant'],
            'intensity': result['intensity'],
            'scores': result['scores'],
            'voice_params': result['voice_params']
        })
        
    except Exception as e:
        logger.error(f"Error analyzing emotion: {str(e)}")
        return JsonResponse({
            'error': 'Error analyzing emotion'
        }, status=500)

@require_http_methods(["POST"])
def analyze_emotion_realtime(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        logger.info(f"Starting emotion analysis for text: {text[:100]}...")
        
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze(text)
        
        logger.log_emotion_scores(result['scores'])
        logger.log_voice_params(result['voice_params'])
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in emotion analysis: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def stream_status(request, session_id):
    """Get status of a streaming TTS session"""
    try:
        status_path = os.path.join(settings.MEDIA_ROOT, 'tts', 'temp', session_id, 'status.json')
        
        if not os.path.exists(status_path):
            return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
            
        with open(status_path, 'r') as f:
            status = json.load(f)
            
        # Add URLs for all processed chunks
        if 'processed_chunks' in status:
            chunk_urls = []
            for i in range(status['processed_chunks']):
                chunk_urls.append(
                    settings.MEDIA_URL + f'tts/temp/{session_id}/chunk_{i}.wav'
                )
            status['chunk_urls'] = chunk_urls
            
        return JsonResponse({'success': True, 'status': status})
        
    except Exception as e:
        logger.error(f"Error getting stream status: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Create a cache for recent requests
@lru_cache(maxsize=100)
def cached_analyze_emotion(text_hash, client_intensity=None):
    """Cache emotion analysis results to prevent duplicate processing"""
    # This function assumes the text hash is unique for each text input
    # and uses it as the cache key to avoid re-analyzing the same text.
    analyzer = EmotionAnalyzer()
    
    # Retrieve the original text from the hash (if needed)
    # In this implementation, we assume the hash is used directly
    # as a unique identifier for the text.
    
    # Perform emotion analysis
    return analyzer.analyze(text_hash, client_intensity)

# In your view function
def analyze_emotion_view(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        client_intensity = data.get('intensity')
        
        # Create a hash of the text to use as a cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Use the cached function
        result = cached_analyze_emotion(text_hash, client_intensity)
        
        return JsonResponse({
            'success': True,
            'emotion': result['dominant'],
            'scores': result['scores'],
            'intensity': result['intensity']
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def generate_audio_streaming(request):
    if request.method == 'POST':
        # Handle streaming TTS generation logic here
        return JsonResponse({'success': True, 'message': 'Streaming TTS not yet implemented'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

