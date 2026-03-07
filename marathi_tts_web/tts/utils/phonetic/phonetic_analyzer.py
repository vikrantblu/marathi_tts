import re
from typing import Dict, List, Set
import logging
from tts.constants.script_constants import PHONETIC_MAP, MATRA_MAP
from tts.constants.text_constants import ABBREVIATIONS

logger = logging.getLogger(__name__)

class PhoneticAnalyzer:
    def __init__(self):
        # Use centralized abbreviations (subset for phonetic analysis)
        self.abbreviations = ABBREVIATIONS.copy()
        
        # Marathi phonetic mappings (from centralized constants)
        self.phonetic_map = PHONETIC_MAP
        
        # Matras (vowel signs) (from centralized constants)
        self.matra_map = MATRA_MAP

    def analyze_text(self, text: str) -> dict:
        """Main method to analyze text for phonetic features"""
        try:
            words = text.split()
            analysis = {
                'syllables': [],
                'phonemes': [],
                'pronunciations': [],
                'word_boundaries': [],
                'abbreviations': []
            }
            
            current_pos = 0
            
            for word in words:
                # Check for abbreviations first
                if '.' in word:
                    full_form = self._expand_abbreviation(word)
                    if full_form:
                        analysis['abbreviations'].append({
                            'abbr': word,
                            'full_form': full_form,
                            'position': current_pos
                        })
                        word = full_form  # Use expanded form for further analysis
                
                # Process the word (expanded if it was an abbreviation)
                syllables = self._split_into_syllables(word)
                phonemes = self._get_phonemes(word)
                pronunciation = self._get_pronunciation(word)
                
                analysis['syllables'].extend(syllables)
                analysis['phonemes'].extend(phonemes)
                analysis['pronunciations'].append({
                    'word': word,
                    'pronunciation': pronunciation,
                    'position': current_pos
                })
                
                analysis['word_boundaries'].append({
                    'position': current_pos,
                    'length': len(word)
                })
                
                current_pos += len(word) + 1  # +1 for space
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in phonetic analysis: {str(e)}")
            return {}

    def _expand_abbreviation(self, text: str) -> str:
        """Expand Marathi abbreviations to their full forms"""
        # Check exact matches first
        if text in self.abbreviations:
            return self.abbreviations[text]
        
        # Check without trailing dot
        if text.endswith('.') and text[:-1] in self.abbreviations:
            return self.abbreviations[text[:-1]]
        
        # Handle multi-part abbreviations
        parts = text.split('.')
        if len(parts) > 1:
            expanded_parts = []
            for part in parts:
                if part:  # Skip empty parts
                    if part in self.abbreviations:
                        expanded_parts.append(self.abbreviations[part])
                    else:
                        expanded_parts.append(part)
            return ' '.join(expanded_parts)
        
        return text

    def get_phonetic_ssml(self, text: str) -> str:
        """Generate SSML with phonetic information"""
        words = text.split()
        ssml_parts = []
        
        for word in words:
            if '.' in word:  # Handle abbreviations
                expanded = self._expand_abbreviation(word)
                ssml_parts.append(f'<say-as interpret-as="text">{expanded}</say-as>')
            else:
                pronunciation = self._get_pronunciation(word)
                if pronunciation != word:
                    ssml_parts.append(f'<phoneme alphabet="ipa" ph="{pronunciation}">{word}</phoneme>')
                else:
                    ssml_parts.append(word)
        
        return ' '.join(ssml_parts)

    def _split_into_syllables(self, word: str) -> list:
        """Split Marathi word into syllables"""
        syllables = []
        current_syllable = ""
        
        for i, char in enumerate(word):
            current_syllable += char
            
            # Check for syllable boundary
            if (i + 1 < len(word) and 
                char not in self.matra_map and 
                word[i + 1] not in self.matra_map):
                syllables.append(current_syllable)
                current_syllable = ""
                
        if current_syllable:
            syllables.append(current_syllable)
            
        return syllables

    def add_pronunciation_markers(self, text: str) -> str:
        """Add pronunciation markers to text"""
        words = text.split()
        marked_text = []
        
        for word in words:
            # Handle abbreviations specially
            if '.' in word:
                marked_text.append(f'<say-as interpret-as="characters">{word}</say-as>')
            else:
                pronunciation = self._get_pronunciation(word)
                if pronunciation != word:
                    marked_text.append(f'<phoneme alphabet="ipa" ph="{pronunciation}">{word}</phoneme>')
                else:
                    marked_text.append(word)
                    
        return ' '.join(marked_text)

    def _get_phonemes(self, word: str) -> list:
        """Extract phonemes from a word"""
        phonemes = []
        i = 0
        
        while i < len(word):
            if i + 1 < len(word) and word[i:i+2] in ['क्ष', 'ज्ञ']:
                phonemes.append(word[i:i+2])
                i += 2
            else:
                phonemes.append(word[i])
                i += 1
                
        return phonemes

    def _get_pronunciation(self, word: str) -> str:
        """Get IPA pronunciation for a word"""
        pronunciation = ""
        i = 0
        
        while i < len(word):
            if i + 1 < len(word) and word[i:i+2] in self.phonetic_map:
                pronunciation += self.phonetic_map[word[i:i+2]]
                i += 2
            elif word[i] in self.phonetic_map:
                pronunciation += self.phonetic_map[word[i]]
                i += 1
            elif word[i] in self.matra_map:
                pronunciation += self.matra_map[word[i]]
                i += 1
            else:
                pronunciation += word[i]
                i += 1
                
        return pronunciation