"""
tts.utils.emotion.emotion_analyzer — standalone version (no Django dependency).

Identical logic to the web-app version; Django settings and the duplicate
setup_logging() block have been removed.
"""
import logging
import math
import re
import os
from typing import Dict, Any, List

from tts.constants.emotion_constants import (
    EMOTION_KEYWORDS, EMOTION_VOICE_PARAMS, EMOTION_SSML_TAG_MAP,
)

# Use stdlib logging — the desktop bridge's _bridge_logging handles handlers.
logger = logging.getLogger("tts.emotion")


class EmotionAnalyzer:
    """Analyzes text to determine emotional content"""

    def __init__(self):
        self.emotion_keywords = EMOTION_KEYWORDS
        self.voice_params = EMOTION_VOICE_PARAMS

    def analyze(self, text: str, client_intensity: float = None) -> Dict[str, Any]:
        """Analyze text to detect emotion with improved intensity calculation"""
        import numpy as np  # lazy import — avoid slow load on every subprocess start
        logger.info("Starting emotion analysis for text length: %d", len(text))

        emotion_scores = {emotion: 0 for emotion in self.emotion_keywords.keys()}
        word_count = len(re.findall(r'\b\w+\b', text))

        total_emotional_weight = 0
        emotional_word_count = 0

        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                if matches > 0:
                    emotional_word_count += matches
                    weight = 0.8
                    total_emotional_weight += matches * weight
                emotion_scores[emotion] += matches
            if word_count > 0:
                emotion_scores[emotion] = emotion_scores[emotion] / word_count

        if sum(emotion_scores.values()) == 0:
            dominant_emotion = 'neutral'
            emotion_scores['neutral'] = 1.0
        else:
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)

        if word_count > 0 and emotional_word_count > 0:
            effective_word_count = max(4, word_count)
            raw_density = total_emotional_weight / effective_word_count
            scaled_density = raw_density * 1.2
            exclamation_count = len(re.findall(r'!', text))
            question_count = len(re.findall(r'\?', text))
            punctuation_factor = min(0.3, (exclamation_count * 0.1) + (question_count * 0.05))
            backend_intensity = min(0.95, max(0.2, (scaled_density * 0.9) + punctuation_factor))
        else:
            backend_intensity = 0.5

        intensity = client_intensity if client_intensity is not None else backend_intensity

        logger.info("Dominant emotion: %s, intensity: %.2f", dominant_emotion, intensity)

        voice_params = self.voice_params.get(dominant_emotion, self.voice_params['neutral'])

        return {
            'scores': emotion_scores,
            'dominant': dominant_emotion,
            'voice_params': voice_params,
            'intensity': intensity,
        }

    def get_emphasis_points(self, text: str) -> Dict[int, float]:
        emphasis_points = {}
        words = re.findall(r'\b\w+\b', text)
        for i, word in enumerate(words):
            if '!' in word or '?' in word:
                emphasis_points[i] = 1.5
            elif word.isupper():
                emphasis_points[i] = 1.3
        return emphasis_points

    def get_emotion_ssml_tag(self, emotion_result: Dict) -> str:
        dominant = emotion_result['dominant']
        intensity = emotion_result['intensity']
        emotion_tag = EMOTION_SSML_TAG_MAP.get(dominant, 'neutral')
        if intensity < 0.6 and emotion_tag != 'neutral':
            return f'<emotion intensity="low" type="{emotion_tag}">'
        elif intensity > 0.8:
            return f'<emotion intensity="high" type="{emotion_tag}">'
        else:
            return f'<emotion intensity="medium" type="{emotion_tag}">'

    def get_word_level_params(self, text: str, base_emotion: Dict) -> List[Dict]:
        words = text.split()
        word_params = []
        for word in words:
            params = base_emotion['voice_params'].copy()
            for emotion, config in self.emotion_keywords.items():
                if any(re.search(pattern, word) for pattern in config):
                    params['pitch'] *= 1.1
                    params['emphasis'] *= 1.2
                    params['volume'] *= 1.1
                    break
            word_params.append({'word': word, 'params': params})
        return word_params

    def apply_emotion_to_audio(self, audio_segment, emotion_params: Dict) -> Any:
        try:
            duration_ms = len(audio_segment)

            def create_envelope(param_value: float, dur: int) -> np.ndarray:
                t = np.linspace(0, dur, int(dur / 10))
                return 1.0 + (param_value - 1.0) * (1 / (1 + np.exp(-0.01 * (t - dur / 2))))

            if emotion_params.get('pitch', 1.0) != 1.0:
                audio_segment = self._apply_pitch_envelope(
                    audio_segment, create_envelope(emotion_params['pitch'], duration_ms))
            if emotion_params.get('speed', 1.0) != 1.0:
                audio_segment = self._apply_speed_envelope(
                    audio_segment, create_envelope(emotion_params['speed'], duration_ms))
            if emotion_params.get('volume', 1.0) != 1.0:
                audio_segment = self._apply_volume_envelope(
                    audio_segment, create_envelope(emotion_params['volume'], duration_ms))
            if emotion_params.get('breathiness'):
                audio_segment = self._apply_breathiness(audio_segment, emotion_params['breathiness'])
            if emotion_params.get('roughness'):
                audio_segment = self._apply_roughness(audio_segment, emotion_params['roughness'])
            if emotion_params.get('vibrato'):
                audio_segment = self._apply_natural_vibrato(audio_segment, emotion_params['vibrato'])
            return audio_segment
        except Exception as e:
            logger.error("Error applying emotion to audio: %s", e)
            return audio_segment

    def _apply_vibrato(self, audio_segment, intensity: float) -> Any:
        try:
            samples = np.array(audio_segment.get_array_of_samples())
            t = np.arange(len(samples)) / audio_segment.frame_rate
            vibrato_rate = 5.0
            vibrato_depth = intensity * 0.3
            modulation = 1.0 + vibrato_depth * np.sin(2 * math.pi * vibrato_rate * t)
            modulated = (samples * modulation).astype(samples.dtype)
            return audio_segment._spawn(modulated.tobytes())
        except Exception as e:
            logger.error("Error applying vibrato: %s", e)
            return audio_segment
