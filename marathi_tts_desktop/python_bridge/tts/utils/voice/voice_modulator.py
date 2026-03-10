import numpy as np
import os
import logging
import tempfile
from typing import Dict, Any, Optional, List
from pydub import AudioSegment
import librosa
from scipy import signal
# Add these imports for audio effects
from pedalboard import Pedalboard, Reverb, Compressor, LadderFilter, Gain
import math  # For pitch shift calculation

# Configure logger
logger = logging.getLogger('tts.voice')

class VoiceModulator:
    """Enhanced voice modulation with professional audio effects"""
    
    def __init__(self):
        """Initialize voice modulator with advanced audio processing"""
        try:
            # Check for advanced audio processing capabilities
            import librosa
            import scipy
            logger.info("Advanced audio processing available (librosa/scipy)")
            
            # Check for professional audio effects
            from pedalboard import Pedalboard
            logger.info("Professional audio effects available (pedalboard)")
        except ImportError as e:
            logger.warning(f"Advanced audio processing unavailable: {str(e)}")
    
    def modulate_voice(self, audio: AudioSegment, options: Dict[str, Any], emphasis_points=None) -> AudioSegment:
        """Apply voice modulation with enhanced audio quality"""
        try:
            logger.info("Starting voice modulation with soothing enhancements")
            logger.debug(f"Modulation options: {options}")
            
            # Get parameters with defaults
            emotion = options.get('emotion', 'neutral')
            pitch = options.get('pitch', 1.0)
            speed = options.get('speed', 1.0)
            volume = options.get('volume', 0)
            
            # First apply basic adjustments
            modified = audio
            
            # Apply pitch adjustment if needed
            if abs(pitch - 1.0) > 0.01:
                modified = self._adjust_pitch(modified, pitch)
                
            # Apply speed adjustment if needed
            if abs(speed - 1.0) > 0.01:
                modified = self._adjust_speed(modified, speed)
                
            # Apply volume adjustment if needed
            if abs(volume) > 0.1:
                modified = self._adjust_volume(modified, volume)
            
            # Apply emotion-specific advanced processing
            if emotion in ['neutral', 'happy']:
                # Additional soothing enhancements for neutral and happy emotions
                try:
                    # Use advanced processing for better quality
                    modified = self._apply_advanced_processing(modified, options)
                    
                    # Apply soothing profile for specific emotions
                    if emotion == 'neutral':
                        modified = self.apply_soothing_profile(modified)
                except Exception as e:
                    logger.error(f"Error in soothing voice modulation: {str(e)}", exc_info=True)
            else:
                # Apply standard advanced processing for other emotions
                try:
                    modified = self._apply_advanced_processing(modified, options)
                except Exception as e:
                    logger.error(f"Error in advanced processing: {str(e)}")
            
            logger.debug("Voice modulation complete")
            return modified
            
        except Exception as e:
            logger.error(f"Error in voice modulation: {str(e)}", exc_info=True)
            # Return original audio if modulation fails
            return audio
    
    def apply_soothing_profile(self, audio: AudioSegment) -> AudioSegment:
        """Apply Google-like soothing voice qualities"""
        try:
            logger.info("Applying soothing voice profile")
            
            # Save to temp file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio.export(temp_path, format="wav")
            
            # Load audio for processing
            y, sr = librosa.load(temp_path, sr=None)
            
            # More refined EQ curve specifically for soothing quality
            y = self._apply_precise_eq(y, sr,
                low_bass=1.2,    # 50-120Hz (fullness)
                mid_bass=1.15,   # 120-250Hz (warmth)
                low_mid=0.97,    # 250-500Hz (reduce muddiness)
                mid=1.05,        # 500-1kHz (voice presence)
                high_mid=1.02,   # 1-2kHz (clarity without harshness)
                low_high=0.96,   # 2-4kHz (reduce sibilance)
                high=0.90,       # 4-8kHz (gentle softening)
                super_high=0.85  # 8-16kHz (remove harshness)
            )
            
            # Add subtle natural breath noise
            breath_noise = np.random.normal(0, 0.0007, len(y))  # Very subtle noise
            breath_noise = signal.filtfilt(*signal.butter(2, [500, 3000], 'bandpass', fs=sr), breath_noise)
            y = y + breath_noise
            
            # Very gentle compression to smooth dynamics
            # Use look-ahead compression for transparent results
            y = self._gentle_compression(y, threshold=0.15, ratio=1.5, attack=20, release=250)
            
            # Add extremely subtle modulation
            y = self._add_subtle_modulation(y, sr, depth=0.03, rate=0.1)
            
            # Normalize with headroom
            max_val = np.max(np.abs(y))
            if max_val > 0:
                y = y * (0.92 / max_val)
            
            # Save to temp file
            out_path = temp_path + "_soothing.wav"
            import soundfile as sf
            sf.write(out_path, y, sr)
            
            # Load result
            result = AudioSegment.from_file(out_path)
            
            # Clean up
            os.unlink(temp_path)
            os.unlink(out_path)
            
            return result
        except Exception as e:
            logger.error(f"Error applying soothing profile: {str(e)}", exc_info=True)
            return audio
    
    def _gentle_compression(self, y, threshold=0.15, ratio=1.5, attack=20, release=250):
        """Apply gentle compression to audio signal"""
        # Simple soft-knee compression implementation
        try:
            # Simple soft-knee compression
            # Create a copy to avoid modifying the original
            compressed = np.copy(y)
            
            # Find samples above threshold
            mask = np.abs(compressed) > threshold
            
            # Apply compression to those samples
            if np.any(mask):
                compressed[mask] = np.sign(compressed[mask]) * (
                    threshold + (np.abs(compressed[mask]) - threshold) / ratio
                )
            
            return compressed
        except Exception as e:
            logger.error(f"Error in compression: {str(e)}", exc_info=True)
            return y
    
    def _add_subtle_modulation(self, y, sr, depth=0.05, rate=0.2):
        """Add extremely subtle pitch/amplitude modulation for natural sound"""
        try:
            # Create a very slow sine wave for modulation
            length_sec = len(y) / sr
            mod_wave = np.sin(2 * np.pi * rate * np.linspace(0, length_sec, len(y)))
            
            # Scale to very small depth
            mod_wave = mod_wave * depth
            
            # Apply to audio (subtle amplitude modulation)
            y_mod = y * (1.0 + mod_wave)
            
            return y_mod
        except Exception as e:
            logger.error(f"Error adding subtle modulation: {str(e)}", exc_info=True)
            return y
            
    def _apply_advanced_processing(self, audio: AudioSegment, options: Dict[str, Any]) -> AudioSegment:
        """Apply advanced audio processing based on emotion"""
        try:
            # Get emotion from options
            emotion = options.get('emotion', 'neutral')
            logger.debug(f"Applying advanced processing for emotion: {emotion}")
            
            # Save to temp file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio.export(temp_path, format="wav")
            
            # Load audio file using librosa for advanced processing
            y, sr = librosa.load(temp_path, sr=None)
            
            # Apply specific EQ curve based on emotion
            if emotion == 'happy':
                # Brighter, more present sound
                y = self._apply_eq_curve(y, sr, bass=1.1, mid=1.15, treble=1.2)
            elif emotion == 'sad':
                # Warmer, softer sound
                y = self._apply_eq_curve(y, sr, bass=1.15, mid=0.9, treble=0.85)
            elif emotion == 'angry':
                # More edge and presence
                y = self._apply_eq_curve(y, sr, bass=1.05, mid=1.2, treble=1.1)
            elif emotion == 'fear':
                # Thin, tense sound
                y = self._apply_eq_curve(y, sr, bass=0.9, mid=1.1, treble=1.15)
            elif emotion == 'surprise':
                # Bright and clear
                y = self._apply_eq_curve(y, sr, bass=1.0, mid=1.2, treble=1.4)
            elif emotion == 'disgust':
                # More midrange nasality
                y = self._apply_eq_curve(y, sr, bass=0.95, mid=1.3, treble=0.9)
            else:
                # Pleasant neutral sound
                y = self._apply_eq_curve(y, sr, bass=1.1, mid=1.1, treble=1.05)
            
            # Save to a new temp file
            out_path = temp_path + "_out.wav"
            import soundfile as sf
            sf.write(out_path, y, sr)
            
            # Load as AudioSegment
            result = AudioSegment.from_file(out_path, format="wav")
            
            # Clean up temp files
            os.unlink(temp_path)
            os.unlink(out_path)
            
            return result
        except Exception as e:
            logger.error(f"Error in advanced processing: {str(e)}", exc_info=True)
            return audio
    
    def _apply_eq_curve(self, y, sr, bass=1.0, mid=1.0, treble=1.0):
        """Apply a 3-band EQ using scipy filters with proper type conversion"""
        try:
            # Convert input to float32 for processing
            y = np.array(y, dtype=np.float32)
            
            # Define crossover frequencies
            bass_cutoff = 250  # Hz
            treble_cutoff = 2500  # Hz
            
            # Design filters
            b_low, a_low = signal.butter(2, bass_cutoff / (sr/2), btype='lowpass')
            b_mid_low, a_mid_low = signal.butter(2, bass_cutoff / (sr/2), btype='highpass')
            b_mid_high, a_mid_high = signal.butter(2, treble_cutoff / (sr/2), btype='lowpass')
            b_high, a_high = signal.butter(2, treble_cutoff / (sr/2), btype='highpass')
            
            # Apply filters to get bands
            y_bass = signal.filtfilt(b_low, a_low, y)
            
            y_mid_tmp = signal.filtfilt(b_mid_low, a_mid_low, y)
            y_mid = signal.filtfilt(b_mid_high, a_mid_high, y_mid_tmp)
            
            y_treble = signal.filtfilt(b_high, a_high, y)
            
            # Apply gains and recombine (using float multiplication)
            result = (y_bass * float(bass) + 
                    y_mid * float(mid) + 
                    y_treble * float(treble))
            
            # Normalize to prevent clipping
            max_val = np.max(np.abs(result))
            if max_val > 1.0:
                result = result / max_val
                
            return result.astype(np.float32)
        except Exception as e:
            logger.error(f"Error applying EQ: {str(e)}", exc_info=True)
            return y
    
    def _apply_precise_eq(self, y, sr, low_bass=1.0, mid_bass=1.0, low_mid=1.0, 
                          mid=1.0, high_mid=1.0, low_high=1.0, high=1.0, super_high=1.0):
        """Apply precise 8-band EQ for soothing voice"""
        try:
            # Convert input to float32 for processing
            y = np.array(y, dtype=np.float32)
            
            # Define band frequencies
            bands = [
                (20, 120, low_bass),     # Low bass
                (120, 250, mid_bass),    # Mid bass
                (250, 500, low_mid),     # Low mids
                (500, 1000, mid),        # Mids
                (1000, 2000, high_mid),  # High mids
                (2000, 4000, low_high),  # Low highs
                (4000, 8001, high),      # Highs
                (8001, sr//2, super_high) # Super highs
            ]
            
            # Process each band
            result = np.zeros_like(y)
            
            for low_freq, high_freq, gain in bands:
                # Skip if gain is 1.0 (no change)
                if abs(gain - 1.0) < 0.01:
                    continue
                    
                # Design bandpass filter
                if low_freq <= 20:
                    b, a = signal.butter(2, high_freq/(sr/2), btype='lowpass')
                elif high_freq >= sr//2 - 100:
                    b, a = signal.butter(2, low_freq/(sr/2), btype='highpass')
                else:
                    b, a = signal.butter(2, [low_freq/(sr/2), high_freq/(sr/2)], btype='bandpass')
                
                # Apply filter to get band
                y_band = signal.filtfilt(b, a, y)
                
                # Apply gain and add to result
                result += y_band * gain
            
            # Mix with original to avoid phase issues (80% processed, 20% original)
            y = y * 0.2 + result * 0.8
                
            # Normalize to prevent clipping
            max_val = np.max(np.abs(y))
            if max_val > 1.0:
                y = y / max_val
            
            return y.astype(np.float32)
        except Exception as e:
            logger.error(f"Error in precise EQ: {str(e)}", exc_info=True)
            return y

    # Basic audio adjustment methods
    def _adjust_pitch(self, audio, pitch_factor):
        """Adjust pitch while preserving duration"""
        try:
            # Export to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio.export(temp_path, format="wav")
            
            # Load with librosa
            y, sr = librosa.load(temp_path, sr=None)
            
            # Pitch shift using librosa
            shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=12 * math.log2(pitch_factor))
            
            # Save modified audio
            out_path = temp_path + "_shifted.wav"
            import soundfile as sf
            sf.write(out_path, shifted, sr)
            
            # Load as AudioSegment
            result = AudioSegment.from_file(out_path, format="wav")
            
            # Clean up temp files
            os.unlink(temp_path)
            os.unlink(out_path)
            
            return result
        except Exception as e:
            logger.error(f"Pitch adjustment failed: {str(e)}", exc_info=True)
            return audio

    def _adjust_speed(self, audio, speed_factor):
        """Adjust speed without changing pitch"""
        try:
            # Simple time stretching with librosa
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio.export(temp_path, format="wav")
            
            # Load with librosa
            y, sr = librosa.load(temp_path, sr=None)
            
            # Time stretch
            stretched = librosa.effects.time_stretch(y, rate=speed_factor)
            
            # Save modified audio
            out_path = temp_path + "_speed.wav"
            import soundfile as sf
            sf.write(out_path, stretched, sr)
            
            # Load as AudioSegment
            result = AudioSegment.from_file(out_path, format="wav")
            
            # Clean up temp files
            os.unlink(temp_path)
            os.unlink(out_path)
            
            return result
        except Exception as e:
            logger.error(f"Speed adjustment failed: {str(e)}", exc_info=True)
            return audio

    def _adjust_volume(self, audio, volume_db):
        """Adjust volume in decibels"""
        try:
            return audio + volume_db
        except Exception as e:
            logger.error(f"Volume adjustment failed: {str(e)}", exc_info=True)
            return audio

    def apply_emotion(self, audio_segment, options):
        """Apply emotion to audio segment based on options"""
        try:
            emotion = options.get('emotion', 'neutral')
            # Get intensity directly from options - CRITICAL CHANGE
            intensity = options.get('emotion_intensity', 1.0)
            
            logger.info(f"Applying emotion {emotion} with intensity {intensity}")
            
            # Get base emotion parameters
            emotion_params = self._get_emotion_params(emotion)
            
            # IMPORTANT: Apply intensity scaling to parameters
            scaled_params = self._scale_params_with_intensity(emotion_params, intensity)
            
            # Apply modulations
            modified_audio = audio_segment
            
            # Apply pitch change based on emotion
            if 'pitch' in scaled_params and scaled_params['pitch'] != 1.0:
                pitch_factor = scaled_params['pitch']
                logger.debug(f"Applying pitch change: {pitch_factor}")
                modified_audio = self.change_pitch(modified_audio, pitch_factor)
            
            # Apply speed change based on emotion
            if 'speed' in scaled_params and scaled_params['speed'] != 1.0:
                speed_factor = scaled_params['speed']
                logger.debug(f"Applying speed change: {speed_factor}")
                modified_audio = self.change_speed(modified_audio, speed_factor)
            
            # Apply volume change based on emotion
            if 'volume' in scaled_params and scaled_params['volume'] != 1.0:
                volume_factor = scaled_params['volume']
                logger.debug(f"Applying volume change: {volume_factor}")
                modified_audio = self.change_volume(modified_audio, volume_factor)
            
            return modified_audio
            
        except Exception as e:
            logger.error(f"Error applying emotion: {str(e)}")
            return audio_segment
        
    def _scale_params_with_intensity(self, params, intensity):
        """Scale emotion parameters based on intensity"""
        # Create a copy to avoid modifying original
        scaled = params.copy()
        
        # Calculate how much to apply emotion (0.2-1.0 range)
        # Even at low intensity (0.1), we still want some emotion (0.2)
        effect_factor = 0.2 + (intensity * 0.8)
        
        # Scale each parameter toward neutral (1.0) based on intensity
        for param in ['pitch', 'speed', 'volume']:
            if param in scaled:
                # Calculate how far parameter is from neutral
                distance_from_neutral = scaled[param] - 1.0
                # Apply scaled distance
                scaled[param] = 1.0 + (distance_from_neutral * effect_factor)
        
        logger.debug(f"Original params: {params}, Scaled with intensity {intensity}: {scaled}")
        return scaled

    def apply_emotion_to_audio(self, audio_segment, emotion_params: Dict) -> Any:
        """Apply emotion modulation to audio"""
        try:
            # Get emotion parameters
            emotion = emotion_params.get('emotion', 'neutral')
            intensity = emotion_params.get('intensity', 0.5)
            
            logger.info(f"Applying {emotion} with intensity {intensity:.2f}")
            
            # Create stronger effect for higher intensity
            # Apply non-linear scaling to make higher intensities more pronounced
            effect_strength = (intensity ** 1.5) * 1.2  # Increased from intensity * 0.5
            
            # Get segment length for transitions
            duration_ms = len(audio_segment)
            
            # Create envelope with stronger effect
            def create_envelope(param_value: float, duration_ms: int) -> np.ndarray:
                """Create smooth parameter envelope"""
                t = np.linspace(0, duration_ms, int(duration_ms/10))  # 10ms steps
                # More pronounced effect
                envelope = 1.0 + ((param_value - 1.0) * effect_strength * 
                                (1 / (1 + np.exp(-0.01 * (t - duration_ms/2)))))
                return envelope
            
            return audio_segment  # Return modified audio when implemented
                
        except Exception as e:
            logger.error(f"Error applying emotion to audio: {str(e)}")
            return audio_segment