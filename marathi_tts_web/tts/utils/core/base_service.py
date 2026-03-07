import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class TTSBaseService(ABC):
    """Base class for TTS services"""
    
    @abstractmethod
    def generate_speech(self, text: str, **kwargs):
        """Generate speech from text"""
        pass
    
    @abstractmethod
    def modify_audio(self, audio_segment, **kwargs):
        """Modify audio parameters"""
        pass