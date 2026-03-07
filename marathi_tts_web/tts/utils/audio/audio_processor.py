import numpy as np
from pydub import AudioSegment
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    logger.warning("Advanced audio processing unavailable. Installing dependencies...")
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "librosa", "soundfile"])
        import librosa
        import soundfile as sf
        AUDIO_PROCESSING_AVAILABLE = True
    except Exception as e:
        logger.error(f"Failed to install audio processing dependencies: {e}")
        AUDIO_PROCESSING_AVAILABLE = False

class AudioProcessor:
    def __init__(self):
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.warning("Audio processor initialized with limited functionality")
        self.sample_rate = 22050
        self.effects = {
            'reverb': self._apply_reverb,
            'normalization': self._normalize_audio,
            'noise_reduction': self._reduce_noise if AUDIO_PROCESSING_AVAILABLE else None,
            'equalization': self._apply_eq if AUDIO_PROCESSING_AVAILABLE else None
        }
        self.chunk_size = 1024 * 1024  # 1MB chunks
        self.supported_formats = ['wav', 'mp3', 'ogg']

    async def process_chunks(self, audio_segments):
        """Process audio chunks asynchronously"""
        try:
            combined = AudioSegment.empty()
            
            for segment in audio_segments:
                # Add crossfade between segments
                if len(combined) > 0:
                    combined = combined.append(segment, crossfade=50)
                else:
                    combined += segment
                    
            # Normalize audio levels
            combined = self.normalize_audio(combined)
            
            return combined
        except Exception as e:
            logger.error(f"Error processing audio chunks: {str(e)}")
            raise

    def normalize_audio(self, audio):
        """Normalize audio levels for consistent volume"""
        try:
            normalized = audio.normalize(headroom=0.1)
            return normalized
        except Exception as e:
            logger.error(f"Audio normalization failed: {str(e)}")
            return audio

    def process_audio(self, audio: AudioSegment, effects_config: Dict = None) -> AudioSegment:
        """Apply audio processing effects"""
        try:
            if not AUDIO_PROCESSING_AVAILABLE:
                logger.warning("Advanced audio processing unavailable - returning unprocessed audio")
                return audio

            if effects_config is None:
                effects_config = {}

            # Convert to numpy array for processing
            samples = np.array(audio.get_array_of_samples())

            # Apply requested effects
            for effect_name, params in effects_config.items():
                if effect_name in self.effects and self.effects[effect_name] is not None:
                    samples = self.effects[effect_name](samples, **params)

            # Convert back to AudioSegment
            processed_audio = AudioSegment(
                samples.tobytes(),
                frame_rate=audio.frame_rate,
                sample_width=audio.sample_width,
                channels=audio.channels
            )

            return processed_audio

        except Exception as e:
            logger.error(f"Audio processing error: {str(e)}")
            return audio

    def _apply_reverb(self, samples: np.ndarray, room_size: float = 0.1) -> np.ndarray:
        """Apply reverb effect"""
        try:
            # Simple convolution reverb
            impulse_response = self._create_impulse_response(room_size)
            reverbed = np.convolve(samples, impulse_response, mode='full')
            return reverbed[:len(samples)]
        except Exception as e:
            logger.error(f"Reverb error: {str(e)}")
            return samples

    def _normalize_audio(self, samples: np.ndarray, target_db: float = -20) -> np.ndarray:
        """Normalize audio levels"""
        try:
            max_amplitude = np.max(np.abs(samples))
            if max_amplitude > 0:
                target_amplitude = 10 ** (target_db / 20)
                normalized = samples * (target_amplitude / max_amplitude)
                return normalized
            return samples
        except Exception as e:
            logger.error(f"Normalization error: {str(e)}")
            return samples

    def _reduce_noise(self, samples: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """Reduce background noise"""
        try:
            # Simple noise reduction using spectral gating
            stft = librosa.stft(samples)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Estimate noise profile
            noise_profile = np.mean(magnitude[:, :10], axis=1, keepdims=True)
            
            # Apply spectral subtraction
            cleaned = magnitude - (noise_profile * strength)
            cleaned = np.maximum(cleaned, 0)
            
            # Reconstruct signal
            cleaned_stft = cleaned * np.exp(1j * phase)
            cleaned_signal = librosa.istft(cleaned_stft)
            
            return cleaned_signal
        except Exception as e:
            logger.error(f"Noise reduction error: {str(e)}")
            return samples

    def _apply_eq(self, samples: np.ndarray, bands: Dict[str, float]) -> np.ndarray:
        """Apply multi-band equalization"""
        try:
            # Simple 3-band EQ
            low_cutoff = 300
            high_cutoff = 3000
            
            # Split into frequency bands
            stft = librosa.stft(samples)
            freqs = librosa.fft_frequencies(sr=self.sample_rate)
            
            # Apply gains to different bands
            low_mask = freqs < low_cutoff
            mid_mask = (freqs >= low_cutoff) & (freqs < high_cutoff)
            high_mask = freqs >= high_cutoff
            
            stft[low_mask] *= bands.get('low', 1.0)
            stft[mid_mask] *= bands.get('mid', 1.0)
            stft[high_mask] *= bands.get('high', 1.0)
            
            # Reconstruct signal
            eq_signal = librosa.istft(stft)
            return eq_signal
            
        except Exception as e:
            logger.error(f"EQ error: {str(e)}")
            return samples

    @staticmethod
    def _create_impulse_response(room_size: float) -> np.ndarray:
        """Create a simple impulse response for reverb"""
        size = int(room_size * 44100)  # Convert room size to samples
        impulse = np.zeros(size)
        impulse[0] = 1
        decay = np.exp(-np.arange(size) / (size * 0.1))
        return impulse * decay