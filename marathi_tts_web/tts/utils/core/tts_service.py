import os
import uuid
import logging
from django.conf import settings
from pathlib import Path
from pydub import AudioSegment
from ..text.text_analyzer import TextAnalyzer
from ..voice.voice_modulator import VoiceModulator
from ..audio.audio_processor import AudioProcessor
from ..phonetic.phonetic_analyzer import PhoneticAnalyzer
from ...models.user_profile import UserProfile
from ...models.tts_feedback import TTSFeedback
from .tts_engine import TTSEngine  # Import TTSEngine
from tts.utils.core.tts_settings import TTS_MEDIA_ROOT, TTS_MEDIA_URL

logger = logging.getLogger(__name__)

class TTSService:
    """High-level TTS service with advanced features"""
    
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.voice_modulator = VoiceModulator()
        self.audio_processor = AudioProcessor()
        self.phonetic_analyzer = PhoneticAnalyzer()
        self.tts_engine = TTSEngine()  # Add TTSEngine instance

    async def generate_speech(self, text: str, user_id: int = None) -> dict:
        """Generate natural-sounding speech with user preferences"""
        try:
            # Get user preferences if available
            user_prefs = await self._get_user_preferences(user_id) if user_id else None

            # Analyze text
            text_analysis = self.text_analyzer.analyze_text(text)
            phonetic_analysis = self.phonetic_analyzer.analyze_text(text)

            # Generate base audio using TTSEngine
            audio_path = self.tts_engine.generate_tts_audio(
                text=text,
                voice_params=user_prefs if user_prefs else {}
            )

            # Apply advanced processing
            audio = await self._generate_base_audio(text, phonetic_analysis)
            processed_audio = self.audio_processor.process_audio(audio, text_analysis)
            
            # Save final audio
            final_path = await self._save_audio(processed_audio)

            return {
                'success': True,
                'audio_url': self.get_audio_url(final_path),
                'analysis': text_analysis,
                'phonetic_data': phonetic_analysis
            }

        except Exception as e:
            logger.error(f"Speech generation failed: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def _get_user_preferences(self, user_id: int) -> dict:
        """Get user's TTS preferences"""
        try:
            profile = await UserProfile.objects.aget(user_id=user_id)
            return {
                'voice': profile.preferred_voice,
                'speed': profile.preferred_speed,
                'pitch': profile.preferred_pitch,
                'volume': profile.preferred_volume,
                'additional': profile.voice_preferences
            }
        except UserProfile.DoesNotExist:
            return {}

    async def _generate_base_audio(self, text: str, phonetic_analysis: dict) -> AudioSegment:
        """Generate base audio using phonetic analysis"""
        try:
            # Initialize empty audio segment
            base_audio = AudioSegment.silent(duration=0)
            
            # Extract phonemes and their durations from analysis
            phonemes = phonetic_analysis.get('phonemes', [])
            
            for phoneme in phonemes:
                # Get the audio sample for the phoneme
                phoneme_audio = self._get_phoneme_audio(
                    phoneme['sound'],
                    duration=phoneme.get('duration', 100),
                    pitch=phoneme.get('pitch', 0),
                    intensity=phoneme.get('intensity', 0)
                )
                
                # Apply crossfade to smooth transitions
                if len(base_audio) > 0:
                    base_audio = base_audio.append(phoneme_audio, crossfade=10)
                else:
                    base_audio = phoneme_audio
                
            # Add natural pauses based on punctuation
            base_audio = self._add_natural_pauses(base_audio, phonetic_analysis.get('pauses', []))
            
            return base_audio
            
        except Exception as e:
            logger.error(f"Base audio generation error: {str(e)}")
            raise

    def _get_processing_config(self, user_prefs: dict = None) -> dict:
        """Get audio processing configuration"""
        config = {
            'normalization': {'target_db': -20},
            'noise_reduction': {'strength': 0.3},
            'equalization': {
                'low': 1.0,
                'mid': 1.1,
                'high': 0.9
            }
        }

        if user_prefs and 'audio_processing' in user_prefs.get('additional', {}):
            config.update(user_prefs['additional']['audio_processing'])

        return config

    async def _save_audio(self, audio: AudioSegment) -> str:
        """Save audio file and return path"""
        try:
            filename = f"tts_{uuid.uuid4()}.wav"
            filepath = os.path.join(TTS_MEDIA_ROOT, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export audio with configured settings
            audio.export(
                filepath,
                format=tts_settings.AUDIO_CONFIG['FORMAT'],
                parameters=[
                    "-ar", str(tts_settings.AUDIO_CONFIG['SAMPLE_RATE']),
                    "-ac", str(tts_settings.AUDIO_CONFIG['CHANNELS'])
                ]
            )
            
            # Return relative path for URL construction
            return os.path.join('tts', filename)
            
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            raise

    async def save_feedback(self, user_id: int, feedback_data: dict) -> bool:
        """Save user feedback"""
        try:
            await TTSFeedback.objects.acreate(
                user_id=user_id,
                **feedback_data
            )
            return True
        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}")
            return False

    def get_audio_url(self, relative_path: str) -> str:
        """Convert relative path to full media URL"""
        return f"{TTS_MEDIA_URL}{os.path.basename(relative_path)}"