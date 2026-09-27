# filepath: tts/models/__init__.py
from .user_input import UserInput, ScanResult
from .user_profile import UserProfile
from .tts_feedback import TTSFeedback
from .correction import MarathiCorrection

__all__ = [
    'UserInput',
    'ScanResult',
    'UserProfile',
    'TTSFeedback',
    'MarathiCorrection',
]