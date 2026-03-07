import re
import logging
from typing import Dict, List, Tuple
from pathlib import Path
import os

# Add fallback for indicnlp
try:
    from indicnlp.tokenize import sentence_tokenize, indic_tokenize
except ImportError:
    # Fallback tokenization
    def sentence_tokenize(text, lang='mar'):
        return re.split('[।.!?]', text)
    
    def indic_tokenize(text):
        return text.split()

logger = logging.getLogger(__name__)

class TextAnalyzer:
    def __init__(self):
        # Use centralized emotion and text patterns
        from tts.constants.emotion_constants import (
            EMOTION_PATTERNS, CONJUNCTION_PATTERNS, CLAUSE_MARKERS,
        )
        self.emotion_patterns = EMOTION_PATTERNS
        self.conjunction_patterns = CONJUNCTION_PATTERNS
        self.clause_markers = CLAUSE_MARKERS

    def analyze_text(self, text: str) -> Dict:
        """Complete text analysis including emotion and emphasis"""
        return {
            "emotion": self.detect_emotion(text),
            "emphasis_points": self.find_emphasis_points(text),
            "prosody": self.analyze_prosody(text)
        }

    def detect_emotion(self, text: str) -> Dict:
        """Detect emotional tone of text"""
        scores = {}
        for emotion, data in self.emotion_patterns.items():
            score = sum(text.count(marker) for marker in data["markers"])
            scores[emotion] = score

        dominant_emotion = max(scores.items(), key=lambda x: x[1])
        return {
            "emotion": dominant_emotion[0],
            "intensity": min(dominant_emotion[1] * 0.2, 1.0),
            "modulation": self.emotion_patterns[dominant_emotion[0]]["modulation"]
        }

    def find_emphasis_points(self, text: str) -> List[Dict]:
        """Identify words that need emphasis"""
        emphasis_points = []
        
        # Important word patterns in Marathi
        emphasis_patterns = {
            'demonstrative': r'(हा|ही|हे|त्या|या|तो|ती|ते)',
            'quantifiers': r'(सर्व|काही|बरेच|अनेक|कित्येक)',
            'negation': r'(नाही|नको|नये)',
            'temporal': r'(आता|सध्या|नंतर|पूर्वी)',
            'imperative': r'([ा]वे$|[ा]वा$)'
        }
        
        current_pos = 0
        words = indic_tokenize.trivial_tokenize(text)
        
        for word in words:
            # Check each pattern
            for pattern_type, pattern in emphasis_patterns.items():
                if re.search(pattern, word):
                    emphasis_points.append({
                        'position': current_pos,
                        'word': word,
                        'type': pattern_type,
                        'intensity': 0.8
                    })
                    break
            
            current_pos += len(word) + 1  # +1 for space
            
        return emphasis_points

    def find_natural_pauses(self, text: str) -> List[Dict]:
        """Find natural pause points in text"""
        pauses = []
        
        # Split into sentences
        sentences = sentence_tokenize.sentence_split(text, lang='mar')
        current_pos = 0
        
        for sentence in sentences:
            # Find clause boundaries
            clause_matches = re.finditer(
                f"({'|'.join(self.clause_markers)})", 
                sentence
            )
            
            for match in clause_matches:
                pauses.append({
                    'position': current_pos + match.start(),
                    'duration': 200,  # ms
                    'type': 'clause'
                })
            
            # Find conjunction points
            conj_matches = re.finditer(
                f"({'|'.join(self.conjunction_patterns)})",
                sentence
            )
            
            for match in conj_matches:
                pauses.append({
                    'position': current_pos + match.start(),
                    'duration': 150,  # ms
                    'type': 'conjunction'
                })
            
            current_pos += len(sentence)
        
        return sorted(pauses, key=lambda x: x['position'])

    def analyze_prosody(self, text: str) -> Dict:
        """Analyze text for prosodic features"""
        return {
            "rhythm": self._analyze_rhythm(text), 
            "intonation": self._analyze_intonation(text),
            "stress_patterns": self._find_stress_patterns(text)
        }

    def _analyze_rhythm(self, text: str) -> Dict:
        """Analyze rhythmic patterns in text"""
        # Count syllables and words
        words = text.split()
        syllable_pattern = r'[अआइईउऊएऐओऔ]|[ाीुूेैोौं]'
        syllable_counts = [len(re.findall(syllable_pattern, word)) for word in words]
        
        return {
            "avg_syllables_per_word": sum(syllable_counts) / len(words) if words else 0,
            "rhythm_variation": max(syllable_counts) - min(syllable_counts) if syllable_counts else 0,
            "word_count": len(words)
        }

    def _analyze_intonation(self, text: str) -> Dict:
        """Analyze intonation patterns"""
        # Detect sentence types and their intonation patterns
        questions = len(re.findall(r'\?', text))
        exclamations = len(re.findall(r'!', text))
        statements = len(re.findall(r'[।॥]', text)) - questions - exclamations
        
        return {
            "sentence_types": {
                "questions": questions,
                "exclamations": exclamations,
                "statements": statements
            },
            "rising_tone": questions > 0,
            "pitch_variation": 1.0 if exclamations > 0 else 0.5
        }

    def _find_stress_patterns(self, text: str) -> List[Dict]:
        """Find stress patterns in text"""
        stress_patterns = []
        words = text.split()
        
        for i, word in enumerate(words):
            # Find long vowels which typically receive stress
            long_vowels = re.findall(r'[ाीूेैोौ]', word)
            if long_vowels:
                stress_patterns.append({
                    "word": word,
                    "position": i,
                    "stress_level": len(long_vowels) / len(word),
                    "stress_type": "long_vowel"
                })
                
        return stress_patterns