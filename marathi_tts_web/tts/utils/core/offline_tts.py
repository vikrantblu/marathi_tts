import os
import uuid
import pyttsx3
import logging
from typing import Optional

logger = logging.getLogger('tts.engine')

class OfflineTTSEngine:
    """Offline TTS Engine using pyttsx3"""
    
    def __init__(self):
        """Initialize the offline TTS engine"""
        self.engine = None
        try:
            self.engine = pyttsx3.init()
            # Configure default properties
            self.engine.setProperty('rate', 150)  # Speed - words per minute
            self.engine.setProperty('volume', 1.0)  # Volume 0-1
            logger.info("Offline TTS Engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize offline TTS engine: {str(e)}")
    
    def is_available(self):
        """Check if the offline engine is available"""
        return self.engine is not None
    
    def get_voices(self):
        """Get available voices"""
        if not self.engine:
            return []
            
        voices = []
        try:
            for voice in self.engine.getProperty('voices'):
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages,
                    'gender': voice.gender
                })
            return voices
        except Exception as e:
            logger.error(f"Failed to get voices: {str(e)}")
            return []
    
    def set_voice(self, voice_id=None, gender=None, language=None):
        """Set voice by ID, gender or language"""
        if not self.engine:
            return False
            
        try:
            voices = self.engine.getProperty('voices')
            
            # Try to find matching voice
            selected_voice = None
            
            if voice_id:
                for voice in voices:
                    if voice.id == voice_id:
                        selected_voice = voice
                        break
                        
            if not selected_voice and (gender or language):
                for voice in voices:
                    matches_gender = not gender or voice.gender == gender
                    matches_language = not language or any(lang.startswith(language) for lang in voice.languages)
                    
                    if matches_gender and matches_language:
                        selected_voice = voice
                        break
            
            # If we found a matching voice, set it
            if selected_voice:
                self.engine.setProperty('voice', selected_voice.id)
                logger.info(f"Set voice to {selected_voice.name}")
                return True
            else:
                logger.warning("No matching voice found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set voice: {str(e)}")
            return False
    
    def generate_speech(self, text, output_dir, rate=None, volume=None):
        """Generate speech from text and return path to audio file"""
        if not self.engine:
            logger.error("Offline TTS engine not available")
            return None
            
        try:
            # Configure properties if specified
            if rate is not None:
                self.engine.setProperty('rate', rate)
            if volume is not None:
                self.engine.setProperty('volume', volume)
                
            # Create output path
            output_file = os.path.join(output_dir, f"offline_tts_{uuid.uuid4()}.wav")
            os.makedirs(output_dir, exist_ok=True)
            
            # Save to file
            self.engine.save_to_file(text, output_file)
            self.engine.runAndWait()
            
            if os.path.exists(output_file):
                logger.info(f"Generated offline audio file: {output_file}")
                return output_file
            else:
                logger.error("Failed to generate offline audio file")
                return None
                
        except Exception as e:
            logger.error(f"Error generating offline speech: {str(e)}")
            return None
    
    def __del__(self):
        """Clean up resources"""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass