import os
import logging

logger = logging.getLogger(__name__)

class MarathiDictionary:
    """Class for Marathi dictionary operations and word suggestions"""
    
    def __init__(self):
        """Initialize the dictionary"""
        self.words = set()
        
        try:
            # Try to load the dictionary file
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            dict_path = os.path.join(base_path, 'dict', 'marathi_dictionary.txt')
            
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word and not word.startswith('//'):
                            self.words.add(word)
                logger.info(f"Loaded {len(self.words)} words from dictionary")
            else:
                logger.warning(f"Dictionary not found at {dict_path}")
        except Exception as e:
            logger.error(f"Error initializing dictionary: {str(e)}")
    
    def exists(self, word):
        """Check if word exists in dictionary"""
        if not word:
            return False
        return word in self.words
    
    def suggest_with_context(self, word, prev_word="", next_word="", prev_context="", next_context="", max_distance=2):
        """Suggest correction for a word based on context"""
        if not word or not self.words:
            return None
            
        # For now, implement simple edit distance-based suggestion
        # This can be enhanced with context-aware suggestions
        best_match = None
        best_distance = float('inf')
        
        # Only check words similar in length to avoid expensive comparisons
        max_length_diff = max_distance  # Use max_distance parameter for length difference too
        target_length = len(word)
        
        for dict_word in self.words:
            # Skip words with too different lengths
            if abs(len(dict_word) - target_length) > max_length_diff:
                continue
                
            # Calculate edit distance
            distance = self._levenshtein_distance(word, dict_word)
            
            if distance < best_distance:
                best_distance = distance
                best_match = dict_word
        
        # Only return suggestions with reasonable confidence
        if best_distance <= max_distance:
            return best_match
        return None
    
    def _levenshtein_distance(self, s1, s2):
        """Calculate the Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]
