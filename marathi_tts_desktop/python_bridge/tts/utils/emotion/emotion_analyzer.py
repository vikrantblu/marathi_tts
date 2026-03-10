import logging
from logging.handlers import RotatingFileHandler
import math
import re
import numpy as np
from typing import Dict, Any, List
from django.conf import settings
import os
from ..logging_config import get_logger
from tts.constants.emotion_constants import (
    EMOTION_KEYWORDS, EMOTION_VOICE_PARAMS, EMOTION_SSML_TAG_MAP,
)

# Use a module-level logger to ensure it's initialized only once
logger = get_logger('tts.emotion')
logger.propagate = False  # Prevent propagation to the root logger

class EmotionAnalyzer:
    """Analyzes text to determine emotional content"""
    
    def __init__(self):
        # Use centralized emotion constants
        self.emotion_keywords = EMOTION_KEYWORDS
        self.voice_params = EMOTION_VOICE_PARAMS

    def analyze(self, text: str, client_intensity: float = None) -> Dict[str, Any]:
        """Analyze text to detect emotion with improved intensity calculation"""
        logger.info(f"Starting emotion analysis for text length: {len(text)}")
        
        # Count emotion keywords
        emotion_scores = {emotion: 0 for emotion in self.emotion_keywords.keys()}
        word_count = len(re.findall(r'\b\w+\b', text))
        
        # Count emotional words with weights
        total_emotional_weight = 0
        emotional_word_count = 0
        
        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                if matches > 0:
                    # Add to general emotional count
                    emotional_word_count += matches
                    # Use higher weight (0.8 instead of default 0.5)
                    weight = 0.8
                    total_emotional_weight += matches * weight
                    
                # Add to emotion score
                emotion_scores[emotion] += matches
            
            # Normalize by text length
            if word_count > 0:
                emotion_scores[emotion] = emotion_scores[emotion] / word_count
        
        # Find dominant emotion
        if sum(emotion_scores.values()) == 0:
            dominant_emotion = 'neutral'
            emotion_scores['neutral'] = 1.0
        else:
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        
        # Calculate intensity based on emotional word density - IMPROVED ALGORITHM
        if word_count > 0 and emotional_word_count > 0:
            # Use smaller denominator for short texts
            effective_word_count = max(4, word_count)
            
            # Calculate raw density with higher base
            raw_density = total_emotional_weight / effective_word_count
            
            # Apply higher scaling factor (1.2 instead of 0.25)
            scaled_density = raw_density * 1.2
            
            # Consider punctuation with higher weights
            exclamation_count = len(re.findall(r'!', text))
            question_count = len(re.findall(r'\?', text))
            punctuation_factor = min(0.3, (exclamation_count * 0.1) + (question_count * 0.05))
            
            # Calculate final intensity with higher multiplier
            # Min 0.2, max 0.95
            backend_intensity = min(0.95, max(0.2, (scaled_density * 0.9) + punctuation_factor))
        else:
            backend_intensity = 0.5  # Default for neutral
        
        # Use client_intensity if provided, otherwise use calculated value
        intensity = client_intensity if client_intensity is not None else backend_intensity
        
        logger.info(f"Emotion scores: {emotion_scores}")
        logger.info(f"Detected dominant emotion: {dominant_emotion}, intensity: {intensity:.2f}")
        
        # Get voice parameters for the dominant emotion
        voice_params = self.voice_params.get(dominant_emotion, self.voice_params['neutral'])
        
        # Return complete analysis result
        result = {
            'scores': emotion_scores,
            'dominant': dominant_emotion,
            'voice_params': voice_params,
            'intensity': intensity  # Now using proper intensity
        }
        
        return result

    def get_emphasis_points(self, text: str) -> Dict[int, float]:
        """Get word emphasis points for text"""
        # Simple implementation - emphasize exclamations and questions
        emphasis_points = {}
        words = re.findall(r'\b\w+\b', text)
        
        for i, word in enumerate(words):
            if '!' in word or '?' in word:
                emphasis_points[i] = 1.5
            elif word.isupper():
                emphasis_points[i] = 1.3
                
        return emphasis_points

    def get_emotion_ssml_tag(self, emotion_result: Dict) -> str:
        """
        Get SSML emotion tag for the detected emotion
        
        Args:
            emotion_result: Result from analyze() method
            
        Returns:
            SSML emotion tag string
        """
        dominant = emotion_result['dominant']
        intensity = emotion_result['intensity']
        
        # Map emotions to SSML emotion tags (from centralized constants)
        emotion_tag_map = EMOTION_SSML_TAG_MAP
        
        # Get mapped tag or default to neutral
        emotion_tag = emotion_tag_map.get(dominant, 'neutral')
        
        # Adjust for intensity
        if intensity < 0.6 and emotion_tag != 'neutral':
            # Weak emotion
            return f'<emotion intensity="low" type="{emotion_tag}">'
        elif intensity > 0.8:
            # Strong emotion
            return f'<emotion intensity="high" type="{emotion_tag}">'
        else:
            # Medium emotion
            return f'<emotion intensity="medium" type="{emotion_tag}">'

    def get_word_level_params(self, text: str, base_emotion: Dict) -> List[Dict]:
        """Get voice parameters for each word based on emotion"""
        words = text.split()
        word_params = []
        
        for word in words:
            params = base_emotion['voice_params'].copy()
            
            # Adjust parameters for emotional words
            for emotion, config in self.emotion_keywords.items():
                if any(re.search(pattern, word) for pattern in config):
                    # Enhance emotional words
                    params['pitch'] *= 1.1
                    params['emphasis'] *= 1.2
                    params['volume'] *= 1.1
                    break
                    
            word_params.append({
                'word': word,
                'params': params
            })
            
        return word_params

    def apply_emotion_to_audio(self, audio_segment, emotion_params: Dict) -> Any:
        """Apply emotional parameters to audio segment with natural transitions"""
        try:
            # Get segment length for transitions
            duration_ms = len(audio_segment)
            
            # Create gradual parameter changes
            def create_envelope(param_value: float, duration_ms: int) -> np.ndarray:
                """Create smooth parameter envelope"""
                t = np.linspace(0, duration_ms, int(duration_ms/10))  # 10ms steps
                # Smooth transition using sigmoid
                envelope = 1.0 + (param_value - 1.0) * (1 / (1 + np.exp(-0.01 * (t - duration_ms/2))))
                return envelope

            # Apply pitch modification with envelope
            if emotion_params.get('pitch', 1.0) != 1.0:
                pitch_env = create_envelope(emotion_params['pitch'], duration_ms)
                audio_segment = self._apply_pitch_envelope(audio_segment, pitch_env)
            
            # Apply speed modification gradually
            if emotion_params.get('speed', 1.0) != 1.0:
                speed_env = create_envelope(emotion_params['speed'], duration_ms)
                audio_segment = self._apply_speed_envelope(audio_segment, speed_env)
            
            # Apply volume envelope
            if emotion_params.get('volume', 1.0) != 1.0:
                volume_env = create_envelope(emotion_params['volume'], duration_ms)
                audio_segment = self._apply_volume_envelope(audio_segment, volume_env)
            
            # Add subtle effects based on emotion
            if emotion_params.get('breathiness'):
                audio_segment = self._apply_breathiness(
                    audio_segment, 
                    emotion_params['breathiness']
                )
            
            if emotion_params.get('roughness'):
                audio_segment = self._apply_roughness(
                    audio_segment, 
                    emotion_params['roughness']
                )
            
            if emotion_params.get('vibrato'):
                audio_segment = self._apply_natural_vibrato(
                    audio_segment, 
                    emotion_params['vibrato']
                )
                
            return audio_segment
            
        except Exception as e:
            logger.error(f"Error applying emotion to audio: {str(e)}")
            return audio_segment

    def _apply_vibrato(self, audio_segment, intensity: float) -> Any:
        """Apply vibrato effect to audio"""
        try:
            import numpy as np
            # Convert audio to numpy array
            samples = np.array(audio_segment.get_array_of_samples())
            
            # Generate vibrato modulation
            time = np.arange(len(samples)) / audio_segment.frame_rate
            vibrato_rate = 5.0  # Hz
            vibrato_depth = intensity * 0.3
            
            modulation = 1.0 + vibrato_depth * np.sin(2 * np.pi * vibrato_rate * time)
            
            # Apply modulation
            modulated = (samples * modulation).astype(samples.dtype)
            
            return audio_segment._spawn(modulated.tobytes())
            
        except Exception as e:
            logger.error(f"Error applying vibrato: {str(e)}")
            return audio_segment

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
        root_logger.handlers.clear()  # Clear existing handlers to prevent duplicates
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Component loggers with their own handlers
        components = ['emotion', 'voice', 'audio', 'text', 'engine', 'views']
        loggers = {}

        for component in components:
            logger_name = f'tts.{component}'
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()  # Clear existing handlers to prevent duplicates
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