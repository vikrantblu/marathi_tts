import re
import logging
from typing import Dict, List
from tts.constants.tts_config import PRONUNCIATION_RULES, CONTEXT_MARKERS

logger = logging.getLogger(__name__)

class PronunciationResolver:
    def __init__(self):
        # Use centralized pronunciation rules
        self.pronunciation_rules = PRONUNCIATION_RULES

        # Use centralized context markers
        self._context_markers = CONTEXT_MARKERS

    def resolve_pronunciation(self, text: str) -> str:
        """Resolve pronunciations based on context"""
        try:
            resolved_text = text
            for word, variants in self.pronunciation_rules.items():
                if word in text:
                    context = self._get_word_context(text, word)
                    pronunciation = self._determine_pronunciation(word, context)
                    resolved_text = resolved_text.replace(word, pronunciation)
            return resolved_text
        except Exception as e:
            logger.error(f"Error resolving pronunciation: {str(e)}")
            return text

    def _get_word_context(self, text: str, word: str) -> str:
        """Get surrounding context of a word"""
        try:
            word_index = text.index(word)
            start = max(0, word_index - 20)
            end = min(len(text), word_index + len(word) + 20)
            return text[start:end]
        except ValueError:
            return ""

    def _determine_pronunciation(self, word: str, context: str) -> str:
        """Determine correct pronunciation based on context"""
        variants = self.pronunciation_rules.get(word, {})
        for context_type, pronunciation in variants.items():
            if any(marker in context for marker in self._get_context_markers(context_type)):
                return pronunciation
        return word

    def _get_context_markers(self, context_type: str) -> List[str]:
        """Get context marker words"""
        return self._context_markers.get(context_type, [])