import re
from typing import List, Dict

class PauseHandler:
    def __init__(self):
        # Define pause patterns with proper weights
        self.PAUSE_PATTERNS = {
            'sentence_end': {
                'markers': {'।', '॥', '.'},
                'ssml': '<break strength="x-strong" time="800ms"/>',
                'weight': 1.0
            },
            'question': {
                'markers': {'?'},
                'ssml': '<break strength="strong" time="300ms"/><prosody pitch="high">?</prosody>',
                'weight': 0.9
            },
            'exclamation': {
                'markers': {'!'},
                'ssml': '<break strength="strong" time="300ms"/><prosody pitch="high">!</prosody>',
                'weight': 0.9
            },
            'major_break': {
                'markers': {';', ':'},
                'ssml': '<break strength="strong" time="200ms"/>',
                'weight': 0.7
            },
            'minor_break': {
                'markers': {','},
                'ssml': '<break strength="medium" time="100ms"/>',
                'weight': 0.5
            }
        }

        # Words that naturally require pauses
        self.NATURAL_PAUSE_WORDS = {
            # Conjunctions
            'परंतु': 0.7,    # but
            'आणि': 0.5,     # and
            'किंवा': 0.5,    # or
            'तथापि': 0.7,   # however
            
            # Transition words
            'म्हणून': 0.6,   # therefore
            'कारण': 0.6,    # because
            'त्यामुळे': 0.6, # consequently
            
            # Emphasizers
            'विशेषतः': 0.5, # especially
            'खासकरून': 0.5  # particularly
        }

    def apply_ssml(self, text: str) -> str:
        """Apply SSML with natural pauses"""
        # Start SSML document
        result = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="mr-IN">']
        
        # Split into sentences while preserving markers
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # Process each sentence
            processed = self._process_sentence(sentence)
            result.append(processed)
        
        # Close SSML
        result.append('</speak>')
        return ' '.join(result)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving markers"""
        pattern = r'([^।॥!?]+[।॥!?])'
        sentences = re.findall(pattern, text)
        remainder = re.sub(pattern, '', text).strip()
        
        if remainder:
            sentences.append(remainder)
        
        return sentences

    def _process_sentence(self, sentence: str) -> str:
        """Process a single sentence for natural pauses"""
        # Handle sentence endings
        for marker_type, config in self.PAUSE_PATTERNS.items():
            for marker in config['markers']:
                if sentence.endswith(marker):
                    return f"{sentence[:-1]}{config['ssml']}{marker}"
        
        # Handle internal pauses
        words = sentence.split()
        result = []
        
        for i, word in enumerate(words):
            # Check for natural pause words
            if word in self.NATURAL_PAUSE_WORDS:
                weight = self.NATURAL_PAUSE_WORDS[word]
                pause_duration = int(400 * weight)
                result.append(f'<break time="{pause_duration}ms"/>{word}')
            # Check for clause markers
            elif any(marker in word for marker in self.PAUSE_PATTERNS['minor_break']['markers']):
                result.append(f"{word}{self.PAUSE_PATTERNS['minor_break']['ssml']}")
            else:
                result.append(word)
        
        return ' '.join(result)

    def find_pauses(self, text: str) -> List[Dict]:
        """Find pause positions with exact timing"""
        pauses = []
        current_pos = 0
        
        # Find all sentence boundaries
        sentence_matches = re.finditer(r'([^।॥!?]+[।॥!?])', text)
        
        for match in sentence_matches:
            sentence = match.group()
            sentence_end = sentence[-1]
            sentence_text = sentence[:-1].strip()
            
            # Add sentence end pause
            if sentence_end in self.PAUSE_PATTERNS['sentence_end']['markers']:
                pauses.append({
                    'position': match.end() - 1,
                    'duration': 800,
                    'type': 'sentence_end'
                })
            
            # Find clause markers within sentence
            for clause_match in re.finditer(r'[,;:]', sentence_text):
                pauses.append({
                    'position': match.start() + clause_match.start(),
                    'duration': 400,
                    'type': 'clause'
                })
        
        return sorted(pauses, key=lambda x: x['position'])

    def apply_pauses(self, text: str, pauses: List[Dict]=None) -> str:
        """Convert text to SSML with proper pauses"""
        return self.apply_ssml(text)
    
    def get_segments(self, text: str) -> List[str]:
        """Split text into segments based on pause points"""
        pauses = self.find_pauses(text)
        segments = []
        last_pos = 0
        
        for pause in sorted(pauses, key=lambda x: x['position']):
            pos = pause['position']
            # Add segment before pause
            segment = text[last_pos:pos].strip()
            if segment:
                segments.append(segment)
            last_pos = pos
        
        # Add final segment
        final_segment = text[last_pos:].strip()
        if final_segment:
            segments.append(final_segment)
            
        return segments
