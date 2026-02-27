import logging
from typing import Dict, Tuple
from tts.constants.script_constants import (
    MODI_RANGE as _MODI_RANGE,
    MODI_DEVANAGARI_MAP as _MODI_DEVANAGARI_MAP,
    MODI_TO_DEVANAGARI_MAP,
)

logger = logging.getLogger(__name__)

class ScriptConverter:
    # Modi Unicode block range (from centralized constants)
    MODI_RANGE: Tuple[int, int] = _MODI_RANGE
    
    # Modi to Devanagari mapping (from centralized constants)
    MODI_DEVANAGARI_MAP: Dict[str, str] = _MODI_DEVANAGARI_MAP

    @classmethod
    def detect_script(cls, text: str) -> str:
        """Detect script type in text"""
        if not text:
            return 'unknown'
            
        if cls.is_modi_script(text):
            return 'modi'
        elif cls.is_devanagari_script(text):
            return 'devanagari'
        return 'unknown'

    @classmethod
    def is_modi_script(cls, text: str) -> bool:
        """Check if text contains Modi script"""
        if not text:
            return False
        return any(cls.MODI_RANGE[0] <= ord(c) <= cls.MODI_RANGE[1] for c in text)

    @classmethod
    def modi_to_devanagari(cls, text: str) -> str:
        """Convert Modi script to Devanagari"""
        if not text:
            return text
            
        for modi_char, devanagari_char in cls.MODI_DEVANAGARI_MAP.items():
            text = text.replace(modi_char, devanagari_char)
        return text

    @classmethod
    def is_devanagari_script(cls, text: str) -> bool:
        """Check if text contains Devanagari script"""
        if not text:
            return False
        return any(0x0900 <= ord(c) <= 0x097F for c in text)

import re

# Modi to Devanagari character mapping (imported from tts.constants.script_constants)
# MODI_TO_DEVANAGARI_MAP is already imported at the top of this module.

def modi_to_devanagari(text):
    """
    Convert Modi script text to Devanagari script.
    
    Args:
        text (str): Text in Modi script
        
    Returns:
        str: Converted text in Devanagari script
    """
    if not text:
        return text
        
    try:
        # Convert character by character
        result = []
        for char in text:
            if 0x11600 <= ord(char) <= 0x1165F:  # Modi Unicode range
                # Direct lookup without string manipulation
                devanagari_char = MODI_TO_DEVANAGARI_MAP.get(char, char)
                result.append(devanagari_char)
            else:
                result.append(char)
                
        # Process special combined characters and joiners
        converted = ''.join(result)
        
        # Handle any specific Modi-Devanagari rules for conjuncts
        # (Add more specific rules if needed)
        
        logger.info(f"Converted {len(text)} Modi characters to Devanagari")
        return converted
        
    except Exception as e:
        logger.error(f"Error converting Modi to Devanagari: {str(e)}")
        # Return original text if conversion fails
        return text